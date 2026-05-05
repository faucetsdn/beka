import threading
import time

from .chopper import Chopper
from .event import EventTimerExpired, EventMessageReceived
from .bgp_message import BgpMessageParser, BgpMessagePacker
from .error import SocketClosedError, IdleError

# Sentinel placed on output queues during shutdown to wake any thread
# blocked in ``Queue.get()`` so it can observe ``_stop_event`` and exit.
_QUEUE_POISON = object()


class Peering(object):
    def __init__(
        self, state_machine, peer_address, socket, route_handler, error_handler=None
    ):
        self.input_stream = None
        self.chopper = None
        self.threads = None
        self.parser = None
        self.packer = None
        self.state_machine = state_machine
        self.peer_address = peer_address[0]
        self.peer_port = peer_address[1]
        self.socket = socket
        self.route_handler = route_handler
        self.error_handler = error_handler
        self.start_time = int(time.time())
        self._stop_event = threading.Event()

    def uptime(self):
        return int(time.time()) - self.start_time

    def run(self):
        self.input_stream = self.socket.makefile(mode="rb")
        self.chopper = Chopper(self.input_stream)
        self.parser = BgpMessageParser()
        self.packer = BgpMessagePacker()
        self.state_machine.open_handler = self.open_handler

        targets = (
            self.send_messages,
            self.print_route_updates,
            self.kick_timers,
            self.receive_messages,
        )
        self.threads = [
            threading.Thread(target=t, name=t.__name__, daemon=True) for t in targets
        ]
        for thread in self.threads:
            thread.start()
        for thread in self.threads:
            thread.join()

    def open_handler(self, capabilities):
        self.parser.capabilities = capabilities
        self.packer.capabilities = capabilities

    def receive_messages(self):
        while not self._stop_event.is_set():
            try:
                message_type, serialised_message = self.chopper.next()
            except SocketClosedError as e:
                if self.error_handler and not self._stop_event.is_set():
                    self.error_handler("Peering %s: %s" % (self.peer_address, e))
                self.shutdown()
                break
            message = self.parser.parse(message_type, serialised_message)
            event = EventMessageReceived(message)
            tick = int(time.time())
            try:
                self.state_machine.event(event, tick)
            except IdleError as e:
                if self.error_handler:
                    self.error_handler("Peering %s: %s" % (self.peer_address, e))
                self.shutdown()
                break

    def send_messages(self):
        while not self._stop_event.is_set():
            message = self.state_machine.output_messages.get()
            if message is _QUEUE_POISON:
                break
            self.socket.send(self.packer.pack(message))

    def empty_message_queue(self):
        while self.state_machine.output_messages.qsize():
            message = self.state_machine.output_messages.get()
            if message is _QUEUE_POISON:
                continue
            self.socket.send(self.packer.pack(message))

    def print_route_updates(self):
        while not self._stop_event.is_set():
            route_update = self.state_machine.route_updates.get()
            if route_update is _QUEUE_POISON:
                break
            self.route_handler(route_update)

    def kick_timers(self):
        # ``Event.wait(timeout)`` returns True as soon as the event is set,
        # giving prompt shutdown without burning CPU between ticks.
        while not self._stop_event.wait(timeout=1):
            tick = int(time.time())
            try:
                self.state_machine.event(EventTimerExpired(), tick)
            except IdleError as e:
                if self.error_handler:
                    self.error_handler("Peering %s: %s" % (self.peer_address, e))
                self.shutdown()
                break

    def shutdown(self):
        if self._stop_event.is_set():
            return
        self._stop_event.set()
        self.empty_message_queue()
        # Unblock any thread parked in ``Queue.get()``. Each consumer
        # checks ``_stop_event`` after waking and exits.
        self.state_machine.output_messages.put(_QUEUE_POISON)
        self.state_machine.route_updates.put(_QUEUE_POISON)
        # Force ``chopper.next()``'s underlying recv to return.
        try:
            self.socket.shutdown(2)  # socket.SHUT_RDWR
        except OSError:
            pass
