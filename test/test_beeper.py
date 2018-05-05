from beeper.bgp_message import BgpMessage, BgpOpenMessage
from beeper.beeper import Beeper
from beeper.event import Event
from beeper.event_message_received import EventMessageReceived
import unittest

class BeeperTestCase(unittest.TestCase):
    def test_open_message_advances_state(self):
        beeper = Beeper()
        self.assertEqual(beeper.state, "active")
        open_message = BgpOpenMessage(4, 60123, 180, 0xC0A8000F)
        output_messages = beeper.event(EventMessageReceived(open_message))
        self.assertEqual(beeper.state, "open_confirm")
        self.assertEqual(len(output_messages), 2)
        self.assertEqual(output_messages[0].type, BgpMessage.OPEN_MESSAGE)
        self.assertEqual(output_messages[1].type, BgpMessage.KEEPALIVE_MESSAGE)

