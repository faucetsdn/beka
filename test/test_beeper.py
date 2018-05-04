from beeper.beeper import Beeper
from beeper.event import Event
from beeper.event_message_received import EventMessageReceived
from beeper.message import Message
import unittest

class BeeperTestCase(unittest.TestCase):
    def test_open_message_advances_state(self):
        beeper = Beeper()
        self.assertEqual(beeper.state, "active")
        output_messages = beeper.event(EventMessageReceived(Message("open")))
        self.assertEqual(beeper.state, "open_confirm")
        self.assertEqual(len(output_messages), 1)

