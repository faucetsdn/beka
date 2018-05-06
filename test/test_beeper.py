from beeper.bgp_message import BgpMessage, BgpOpenMessage, BgpUpdateMessage, BgpKeepaliveMessage
from beeper.beeper import Beeper
from beeper.event import Event, EventTimerExpired, EventMessageReceived
from beeper.ip4 import ip_string_to_number, IP4Prefix
from beeper.route import Route
import unittest

class BeeperTestCase(unittest.TestCase):
    def test_open_message_advances_state(self):
        beeper = Beeper(my_as=65001, peer_as=65002, my_id="1.1.1.1", peer_id="2.2.2.2", hold_time=240)
        self.assertEqual(beeper.state, "active")
        open_message = BgpOpenMessage(4, 65002, 240, ip_string_to_number("2.2.2.2"))
        self.assertEqual(len(beeper.output_messages), 0)
        beeper.event(EventMessageReceived(open_message))
        self.assertEqual(beeper.state, "open_confirm")
        self.assertEqual(len(beeper.output_messages), 2)
        self.assertEqual(beeper.output_messages[0].type, BgpMessage.OPEN_MESSAGE)
        self.assertEqual(beeper.output_messages[1].type, BgpMessage.KEEPALIVE_MESSAGE)

    def test_expired_keepalive_timer_generates_keepalive_message(self):
        # TODO put Beeper in the right state here
        hold_time = 240
        keepalive_time = 80
        beeper = Beeper(my_as=65001, peer_as=65002, my_id="1.1.1.1", peer_id="2.2.2.2", hold_time=240)
        tick = beeper.timers["keepalive"] + keepalive_time
        self.assertEqual(len(beeper.output_messages), 0)
        beeper.event(EventTimerExpired(tick))
        self.assertEqual(len(beeper.output_messages), 1)
        self.assertEqual(beeper.output_messages[0], BgpKeepaliveMessage())

    def test_update_message_adds_route(self):
        # TODO put Beeper in the right state here
        beeper = Beeper(my_as=65001, peer_as=65002, my_id="1.1.1.1", peer_id="2.2.2.2", hold_time=240)
        path_attributes = {
            "next_hop" : "5.4.3.2",
            "as_path" : "65032 65011 65002",
            "origin" : "EGP"
            }
        route_attributes = {
            "prefix" : IP4Prefix("192.168.0.0", 16),
            "next_hop" : "5.4.3.2",
            "as_path" : "65032 65011 65002",
            "origin" : "EGP"
            }
        message = BgpUpdateMessage([], path_attributes, [IP4Prefix("192.168.0.0", 16)])
        beeper.event(EventMessageReceived(message))
        self.assertEqual(len(beeper.route_updates), 1)
        self.assertEqual(beeper.route_updates[0], Route(**route_attributes))
