from gevent.pool import Pool
from gevent.server import StreamServer

from beeper.state_machine import StateMachine
from beeper.peering import Peering

DEFAULT_BGP_PORT = 179

class Beeper(object):
    def __init__(self, local_address, bgp_port,
            peers, peer_up_handler, peer_down_handler,
            route_handler, error_handler):
        self.local_address = local_address
        self.bgp_port = bgp_port
        self.peers_by_neighbor = {}
        self.peerings = []
        self.peer_up_handler = peer_up_handler
        self.peer_down_handler = peer_down_handler
        self.route_handler = route_handler
        self.error_handler = error_handler
        self.stream_server = None

        if not self.bgp_port:
            self.bgp_port = DEFAULT_BGP_PORT

        for peer in peers:
            self.peers_by_neighbor[peer["neighbor"]] = peer

    def run(self):
        pool = Pool(100)
        self.stream_server = StreamServer((self.local_address, self.bgp_port), self.handle, spawn=pool)
        self.stream_server.serve_forever()

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

    def shutdown(self):
        if self.stream_server:
            self.stream_server.stop()
        for peering in self.peerings:
            peering.shutdown()
