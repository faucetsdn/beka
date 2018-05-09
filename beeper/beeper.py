from gevent.server import StreamServer

from beeper.state_machine import StateMachine
from beeper.peering import Peering

BGP_PORT = 179

class Beeper(object):
    def __init__(self, local_address, peers, peer_up_handler, peer_down_handler, route_handler, error_handler):
        self.local_address = local_address
        self.peers_by_neighbor = {}
        self.peerings = []
        self.peer_up_handler = peer_up_handler
        self.peer_down_handler = peer_down_handler
        self.route_handler = route_handler
        self.error_handler = error_handler

        for peer in peers:
            self.peers_by_neighbor[peer["neighbor"]] = peer

    def run(self):
        stream_server = StreamServer((self.local_address, BGP_PORT), self.handle)
        stream_server.serve_forever()

    def handle(self, socket, address):
        neighbor = address[0]
        if neighbor not in self.peers_by_neighbor:
            self.error_handler("Rejecting connection from %s:%d" % address)
            socket.close()
            return
        state_machine = StateMachine(**self.peers_by_neighbor[neighbor])
        peering = Peering(state_machine, address, socket, self.route_handler)
        self.peerings.append(peering)
        self.peer_up_handler("Peer up %s" % neighbor)
        peering.run()
        self.peer_down_handler("Peer down %s" % neighbor)
        self.peerings.remove(peering)