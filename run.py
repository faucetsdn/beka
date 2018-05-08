from beeper.beeper import Beeper
from beeper.chopper import Chopper
from beeper.socket_io import SocketIO
from beeper.event import EventTimerExpired, EventMessageReceived
from beeper.bgp_message import BgpMessage, parse_bgp_message

import sys
import yaml
import time

from gevent.server import StreamServer
from gevent import spawn, sleep, joinall
from queue import Queue

BGP_PORT = 179
ADDRESS = '0.0.0.0'

def printmsg(msg):
    sys.stderr.write("%s\n" % msg)
    sys.stderr.flush()

class Peering(object):
    def __init__(self, beeper):
        self.beeper = beeper

    def run(self, socket):
        self.socket = socket
        printmsg("Creating SocketIO")
        self.input_stream = socket.makefile(mode="rb")
        printmsg("Creating Chopper")
        self.chopper = Chopper(self.input_stream)
        printmsg("Creating greenlets collection")
        self.greenlets = []
        printmsg("Starting greenlets")

        self.greenlets.append(spawn(self.send_messages))
        self.greenlets.append(spawn(self.print_route_updates))
        self.greenlets.append(spawn(self.kick_timers))
        self.greenlets.append(spawn(self.receive_messages))

        printmsg("Made greenlets, doing a joinall()")
        joinall(self.greenlets)

    def receive_messages(self):
        while True:
            sleep(0)
            printmsg("Receiving message from chopper")
            message_type, serialised_message = self.chopper.next()
            printmsg("Decoding message")
            message = parse_bgp_message(message_type, serialised_message)
            printmsg(str(message))
            printmsg("Sending event to beeper")
            event = EventMessageReceived(message)
            tick = int(time.time())
            self.beeper.event(event, tick)

    def send_messages(self):
        while True:
            sleep(0)
            if self.beeper.output_messages.qsize() > 0:
                message = self.beeper.output_messages.get()
                printmsg("Sending message: %s" % str(message))
                self.socket.send(BgpMessage.pack(message))

    def print_route_updates(self):
        while True:
            sleep(0)
            if self.beeper.route_updates.qsize() > 0:
                route = self.beeper.route_updates.get()
                printmsg("New route received: %s" % route)

    def kick_timers(self):
        while True:
            sleep(1)
            tick = int(time.time())
            self.beeper.event(EventTimerExpired(), tick)

class Server(object):
    def run(self):
        # TODO make this multiplex different IP/AS combos
        printmsg("Loading config")
        with open("beeper.yaml") as file:
            config = yaml.load(file.read())
        printmsg("Creating beeper")
        peer = config["peers"][0]
        beeper = Beeper(**peer)
        self.peering = Peering(beeper)

        printmsg("Creating socket")
        stream_server = StreamServer((ADDRESS, BGP_PORT), self.handle)
        stream_server.serve_forever()

    def handle(self, socket, address):
        printmsg("Accepted connection from %s" % str(address))
        self.peering.run(socket)

if __name__ == "__main__":
    server = Server()
    server.run()
