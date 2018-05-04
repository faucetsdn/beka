from beeper.bgp_message import BgpMessage, parse_bgp_message, BgpOpenMessage, BgpKeepaliveMessage
import unittest

class BgpMessageTestCase(unittest.TestCase):
    def test_open_message_parses(self):
        serialised_message = b"\x04\xfe\x09\x00\xb4\xc0\xa8\x00\x0f\x00"
        message = parse_bgp_message(BgpMessage.OPEN_MESSAGE, serialised_message)
        self.assertEqual(message.version, 4)
        self.assertEqual(message.peer_as, 65033)
        self.assertEqual(message.hold_time, 180)
        self.assertEqual(message.identifier, 0xC0A8000F)

    def test_open_message_packs(self):
        expected_serialised_message = b"\x04\xfe\x09\x00\xb4\xc0\xa8\x00\x0f\x00"
        message = BgpOpenMessage(4, 65033, 180, 0xC0A8000F)
        serialised_message = message.pack()
        self.assertEqual(serialised_message, expected_serialised_message)

    def test_keepalive_message_parses(self):
        serialised_message = b""
        message = parse_bgp_message(BgpMessage.KEEPALIVE_MESSAGE, serialised_message)

    def test_keepalive_message_packs(self):
        expected_serialised_message = b""
        message = BgpKeepaliveMessage()
        serialised_message = message.pack()
        self.assertEqual(serialised_message, expected_serialised_message)