from beeper.bgp_message import BgpMessage, BgpOpenMessage
from beeper.beeper import Beeper
from beeper.event import Event
from beeper.event_message_received import EventMessageReceived
from beeper.ip4 import ip_string_to_number
import unittest

class BeeperTestCase(unittest.TestCase):
    def test_open_message_advances_state(self):
        beeper = Beeper(my_as=65001, peer_as=65002, my_id="1.1.1.1", peer_id="2.2.2.2", hold_time=240)
        self.assertEqual(beeper.state, "active")
        open_message = BgpOpenMessage(4, 65002, 240, ip_string_to_number("2.2.2.2"))
        output_messages = beeper.event(EventMessageReceived(open_message))
        self.assertEqual(beeper.state, "open_confirm")
        self.assertEqual(len(output_messages), 2)
        self.assertEqual(output_messages[0].type, BgpMessage.OPEN_MESSAGE)
        self.assertEqual(output_messages[1].type, BgpMessage.KEEPALIVE_MESSAGE)

