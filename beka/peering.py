import time

from eventlet import sleep, GreenPool
from eventlet.queue import Queue
import eventlet.greenthread as greenthread

from .chopper import Chopper
from .event import EventTimerExpired, EventMessageReceived
from .bgp_message import BgpMessageParser, BgpMessagePacker
from .error import SocketClosedError, IdleError

class Peering(object):

    def __init__(self, state_machine, peer_address, socket, route_handler, error_handler=None):
        self.input_stream = None
        self.chopper = None
        self.pool = None
        self.eventlets = None
        self.parser = None
        self.packer = None
        self.state_machine = state_machine
        self.peer_address = peer_address[0]
        self.peer_port = peer_address[1]
        self.socket = socket
        self.route_handler = route_handler
        self.error_handler = error_handler
        self.start_time = int(time.time())

    def uptime(self):
        return int(time.time()) - self.start_time

    def run(self):
        self.input_stream = self.socket.makefile(mode="rb")
        self.chopper = Chopper(self.input_stream)
        self.pool = GreenPool()
        self.parser = BgpMessageParser()
        self.packer = BgpMessagePacker()
        self.state_machine.open_handler = self.open_handler
        self.eventlets = []

        self.eventlets.append(self.pool.spawn(self.send_messages))
        self.eventlets.append(self.pool.spawn(self.print_route_updates))
        self.eventlets.append(self.pool.spawn(self.kick_timers))
        self.eventlets.append(self.pool.spawn(self.receive_messages))

        self.pool.waitall()

    def open_handler(self, capabilities):
        self.parser.capabilities = capabilities
        self.packer.capabilities = capabilities

    def receive_messages(self):
        while True:
            sleep(0)
            try:
                message_type, serialised_message = self.chopper.next()
            except SocketClosedError as e:
                if self.error_handler:
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
        while True:
            sleep(0)
            message = self.state_machine.output_messages.get()
            self.socket.send(self.packer.pack(message))

    def empty_message_queue(self):
        while self.state_machine.output_messages.qsize():
            message = self.state_machine.output_messages.get()
            self.socket.send(self.packer.pack(message))

    def print_route_updates(self):
        while True:
            sleep(0)
            route_update = self.state_machine.route_updates.get()
            self.route_handler(route_update)

    def kick_timers(self):
        while True:
            sleep(1)
            tick = int(time.time())
            try:
                self.state_machine.event(EventTimerExpired(), tick)
            except IdleError as e:
                if self.error_handler:
                    self.error_handler("Peering %s: %s" % (self.peer_address, e))
                self.shutdown()
                break

    def shutdown(self):
        self.empty_message_queue()
        for eventlet in self.eventlets:
            eventlet.kill()
