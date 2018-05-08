from beeper.beeper import Beeper
from beeper.chopper import Chopper
from beeper.socket_io import SocketIO
from beeper.event import EventTimerExpired, EventMessageReceived
from beeper.bgp_message import BgpMessage, parse_bgp_message

import sys
import yaml
import time

from gevent.server import StreamServer

BGP_PORT = 179
ADDRESS = '0.0.0.0'

def printmsg(msg):
    sys.stderr.write("%s\n" % msg)
    sys.stderr.flush()

def fsm(socket, beeper):
    tick = int(time.time())
    input_stream = SocketIO(socket)
    chopper = Chopper(input_stream)

    while True:
        tick = int(time.time())
        printmsg("Handling timers at %d" % tick)
        printmsg(beeper.timers)
        beeper.event(EventTimerExpired(), tick)
        printmsg("Receiving message from chopper")
        message_type, serialised_message = chopper.next()
        printmsg("Decoding message")
        message = parse_bgp_message(message_type, serialised_message)
        printmsg(str(message))
        printmsg("Sending event to beeper")
        event = EventMessageReceived(message)
        beeper.event(event, tick)
        printmsg("Messages from beeper: %s" % [str(x) for x in beeper.output_messages])
        # send them
        while len(beeper.output_messages) > 0:
            message = beeper.output_messages.popleft()
            socket.send(BgpMessage.pack(message))

        # print route updates
        while len(beeper.route_updates) > 0:
            route = beeper.route_updates.popleft()
            printmsg("New route received: %s" % route)

class Server(object):
    def handle(self, socket, address):
        printmsg("Accepted connection from %s" % str(address))
        fsm(socket, self.beeper)

    def run(self):
        printmsg("Loading config")
        with open("beeper.yaml") as file:
            self.config = yaml.load(file.read())
        printmsg("Creating beeper")
        self.peer = self.config["peers"][0]
        self.beeper = Beeper(**self.peer)

        printmsg("Creating socket")
        server = StreamServer((ADDRESS, BGP_PORT), self.handle)
        server.serve_forever()

if __name__ == "__main__":
    server = Server()
    server.run()
