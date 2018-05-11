from gevent import spawn, sleep, joinall, killall
from gevent.queue import Queue

from beeper.chopper import Chopper
from beeper.event import EventTimerExpired, EventMessageReceived
from beeper.bgp_message import BgpMessage, parse_bgp_message
from beeper.route import RouteAddition, RouteRemoval
from beeper.error import SocketClosedError

import time

class Peering(object):
    def __init__(self, state_machine, peer_address, socket, route_handler):
        self.state_machine = state_machine
        self.peer_address = peer_address[0]
        self.peer_port = peer_address[1]
        self.socket = socket
        self.route_handler = route_handler

    def run(self):
        self.input_stream = self.socket.makefile(mode="rb")
        self.chopper = Chopper(self.input_stream)
        self.greenlets = []

        self.greenlets.append(spawn(self.send_messages))
        self.greenlets.append(spawn(self.print_route_updates))
        self.greenlets.append(spawn(self.kick_timers))
        self.greenlets.append(spawn(self.receive_messages))

        joinall(self.greenlets)

    def receive_messages(self):
        while True:
            sleep(0)
            try:
                message_type, serialised_message = self.chopper.next()
            except SocketClosedError as e:
                self.shutdown()
                break
            message = parse_bgp_message(message_type, serialised_message)
            event = EventMessageReceived(message)
            tick = int(time.time())
            self.state_machine.event(event, tick)

    def send_messages(self):
        while True:
            sleep(0)
            message = self.state_machine.output_messages.get()
            self.socket.send(BgpMessage.pack(message))

    def print_route_updates(self):
        while True:
            sleep(0)
            route = self.state_machine.route_updates.get()
            if isinstance(route, RouteAddition):
                self.route_handler("%s: New route received: %s" % (self.peer_address, route))
            elif isinstance(route, RouteRemoval):
                self.route_handler("%s: Route removed: %s" % (self.peer_address, route))

    def kick_timers(self):
        while True:
            sleep(1)
            tick = int(time.time())
            self.state_machine.event(EventTimerExpired(), tick)

    def shutdown(self):
        killall(self.greenlets)
