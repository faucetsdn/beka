import unittest

from beka.beka import Beka
from beka.route import RouteAddition
from beka.ip import IPPrefix, IPAddress

class BekaTestCase(unittest.TestCase):
    def setUp(self):
        self.beka = Beka(
            local_address=None,
            bgp_port=None,
            local_as=None,
            router_id=None,
            peer_up_handler=None,
            peer_down_handler=None,
            route_handler=None,
            error_handler=None
        )

    def test_add_neighbor_must_be_passive(self):
        with self.assertRaises(ValueError) as context:
            self.beka.add_neighbor("active", "10.1.1.1", 65004)

        self.assertTrue("Only passive BGP supported" in str(context.exception))

    def test_add_neighbor_cannot_add_twice(self):
        self.assertFalse(self.beka.peers)
        self.beka.add_neighbor("passive", "10.1.1.1", 65004)
        self.assertTrue(self.beka.peers)
        self.assertEqual(self.beka.peers["10.1.1.1"], {
            "peer_ip": "10.1.1.1",
            "peer_as": 65004
        })

        with self.assertRaises(ValueError) as context:
            self.beka.add_neighbor("passive", "10.1.1.1", 65004)

        self.assertTrue("Peer already added" in str(context.exception))

    def test_add_route_adds_route(self):
        self.beka.add_route("10.1.0.0/16", "192.168.1.3")
        self.assertEqual(self.beka.routes_to_advertise[0],
            RouteAddition(
                prefix=IPPrefix.from_string("10.1.0.0/16"),
                next_hop=IPAddress.from_string("192.168.1.3"),
                as_path="",
                origin="IGP"
            )
        )

    def test_listening_on(self):
        beka = Beka(
            local_address='1.2.3.4',
            bgp_port=12345,
            local_as=23456,
            router_id='4.3.2.1',
            peer_up_handler=None,
            peer_down_handler=None,
            route_handler=None,
            error_handler=None
        )
        self.assertTrue(beka.listening_on('1.2.3.4', 12345))
        self.assertFalse(beka.listening_on('1.2.3.4', 23456))
        self.assertFalse(beka.listening_on('4.3.2.1', 12345))
        self.assertFalse(beka.listening_on('4.3.2.1', 23456))
        self.assertFalse(beka.listening_on('8.8.8.8', 53))

