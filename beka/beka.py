from copy import copy

from .stream_server import StreamServer

from .state_machine import StateMachine
from .peering import Peering
from .route import RouteAddition, RouteRemoval
from .ip import IPAddress, IPPrefix

DEFAULT_BGP_PORT = 179

class Beka(object):
    def __init__(self, local_address, bgp_port, local_as,
            router_id, peer_up_handler, peer_down_handler,
            route_handler, error_handler):
        self.local_address = local_address
        self.bgp_port = bgp_port
        self.local_as = local_as
        self.router_id = router_id
        self.peer_up_handler = peer_up_handler
        self.peer_down_handler = peer_down_handler
        self.route_handler = route_handler
        self.error_handler = error_handler

        self.peers = {}
        self.peerings = []
        self.stream_server = None
        self.routes_to_advertise = []

        if not self.bgp_port:
            self.bgp_port = DEFAULT_BGP_PORT

    def add_neighbor(self, connect_mode, peer_ip, peer_as):
        if connect_mode != "passive":
            raise ValueError("Only passive BGP supported")
        if peer_ip in self.peers:
            raise ValueError("Peer already added: %s %d" % (peer_ip, peer_as))

        self.peers[peer_ip] = {
            "peer_ip": peer_ip,
            "peer_as": peer_as
        }

    def add_route(self, prefix, next_hop):
        self.routes_to_advertise.append(
            RouteAddition(
                prefix=IPPrefix.from_string(prefix),
                next_hop=IPAddress.from_string(next_hop),
                as_path="",
                origin="IGP"
            )
        )

    def neighbor_states(self):
        states = []
        for peering in self.peerings:
            states.append((
                peering.peer_address,
                {
                    'info': {
                        'uptime': peering.uptime()
                    }
                }
            ))

        return states

    def run(self):
        self.stream_server = StreamServer((self.local_address, self.bgp_port), self.handle)
        self.stream_server.serve_forever()

    def handle(self, socket, address):
        peer_ip = address[0]
        if peer_ip not in self.peers:
            if self.error_handler:
                self.error_handler("Rejecting connection from %s:%d" % address)
            socket.close()
            return
        peer = self.peers[peer_ip]
        state_machine = StateMachine(
            local_as=self.local_as,
            peer_as=peer["peer_as"],
            router_id=self.router_id,
            local_address=self.local_address,
            neighbor=peer["peer_ip"]
        )
        state_machine.routes_to_advertise = copy(self.routes_to_advertise)
        peering = Peering(state_machine, address, socket, self.route_handler, error_handler=self.error_handler)
        self.peerings.append(peering)
        self.peer_up_handler(peer_ip, peer["peer_as"])
        peering.run()
        self.peer_down_handler(peer_ip, peer["peer_as"])
        self.peerings.remove(peering)

    def shutdown(self):
        if self.stream_server:
            self.stream_server.stop()
        for peering in self.peerings:
            peering.shutdown()

    def listening_on(self, address, port):
        return self.local_address == address and self.bgp_port == port
