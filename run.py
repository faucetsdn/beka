from beeper.beeper import Beeper
from beeper.chopper import Chopper
from beeper.event import EventTimerExpired, EventMessageReceived
from beeper.bgp_message import BgpMessage, parse_bgp_message
from beeper.route import RouteAddition, RouteRemoval
from beeper.error import SocketClosedError

import sys
import yaml
import time

from gevent.server import StreamServer
from gevent import spawn, sleep, joinall, killall
from queue import Queue

BGP_PORT = 179

def printmsg(msg):
    sys.stderr.write("%s\n" % msg)
    sys.stderr.flush()

class Peering(object):
    def __init__(self, beeper, peer_address, socket, route_handler):
        self.beeper = beeper
        self.peer_address = peer_address[0]
        self.peer_port = peer_address[1]
        self.socket = socket
        self.route_handler = route_handler

    def printmsg(self, msg):
        printmsg("%s:%d %s" % (self.peer_address, self.peer_port, msg))

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
                killall(self.greenlets)
                break
            message = parse_bgp_message(message_type, serialised_message)
            event = EventMessageReceived(message)
            tick = int(time.time())
            self.beeper.event(event, tick)

    def send_messages(self):
        while True:
            sleep(0)
            if self.beeper.output_messages.qsize() > 0:
                message = self.beeper.output_messages.get()
                self.socket.send(BgpMessage.pack(message))

    def print_route_updates(self):
        while True:
            sleep(0)
            if self.beeper.route_updates.qsize() > 0:
                route = self.beeper.route_updates.get()
                if type(route) == RouteAddition:
                    self.route_handler("%s: New route received: %s" % (self.peer_address, route))
                elif type(route) == RouteRemoval:
                    self.route_handler("%s: Route removed: %s" % (self.peer_address, route))

    def kick_timers(self):
        while True:
            sleep(1)
            tick = int(time.time())
            self.beeper.event(EventTimerExpired(), tick)

class PeeringHost(object):
    def __init__(self, local_address, peers, peer_up_handler, peer_down_handler, route_handler):
        self.local_address = local_address
        self.peers_by_neighbor = {}
        self.peerings = []
        self.peer_up_handler = peer_up_handler
        self.peer_down_handler = peer_down_handler
        self.route_handler = route_handler

        for peer in peers:
            self.peers_by_neighbor[peer["neighbor"]] = peer

    def start_server(self):
        printmsg("Creating socket on %s" % self.local_address)
        stream_server = StreamServer((self.local_address, BGP_PORT), self.handle)
        stream_server.serve_forever()

    def handle(self, socket, address):
        printmsg("Accepted connection from %s" % str(address))
        neighbor = address[0]
        if neighbor not in self.peers_by_neighbor:
            printmsg("Rejecting connection from %s:%d" % address)
            socket.close()
            return
        beeper = Beeper(**self.peers_by_neighbor[neighbor])
        peering = Peering(beeper, address, socket, self.route_handler)
        self.peerings.append(peering)
        self.peer_up_handler("Peer up %s" % neighbor)
        peering.run()
        self.peer_down_handler("Peer down %s" % neighbor)
        printmsg("Peering %s finished, removing" % neighbor)
        self.peerings.remove(peering)

class Server(object):
    def __init__(self):
        self.peering_hosts = []
        self.greenlets = []

    def run(self):
        with open("beeper.yaml") as file:
            config = yaml.load(file.read())
        self.peers_per_address = {}
        for peer in config["peers"]:
            if peer["local_address"] not in self.peers_per_address:
                self.peers_per_address[peer["local_address"]] = []
            self.peers_per_address[peer["local_address"]].append(peer)

        for address, peers in self.peers_per_address.items():
            peering_host = PeeringHost(address, peers, self.peer_up_handler, self.peer_down_handler, self.route_handler)
            self.greenlets.append(spawn(peering_host.start_server))
        joinall(self.greenlets)

    def peer_up_handler(self, msg):
        printmsg("[Peer up] %s" % msg)

    def peer_down_handler(self, msg):
        printmsg("[Peer down] %s" % msg)

    def route_handler(self, msg):
        printmsg("[New route] %s" % msg)

if __name__ == "__main__":
    server = Server()
    server.run()
