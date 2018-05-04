from beeper.bgp_message import BgpMessage, parse_bgp_message
import unittest

class BgpMessageTestCase(unittest.TestCase):
    def test_open_message_parses(self):
        serialised_message = b"\x04\xfe\x09\x00\xb4\xc0\xa8\x00\x0f\x00"
        message = parse_bgp_message(BgpMessage.OPEN_MESSAGE, serialised_message)
        self.assertEqual(message.version, 4)
        self.assertEqual(message.peer_as, 65033)
        self.assertEqual(message.hold_time, 180)
        self.assertEqual(message.identifier, 0xC0A8000F)
