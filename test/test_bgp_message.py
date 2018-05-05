from beeper.bgp_message import BgpMessage, parse_bgp_message, BgpOpenMessage, BgpKeepaliveMessage
from beeper.ip4 import IP4Prefix
import struct
import unittest

def build_byte_string(hex_stream):
    values = [int(x, 16) for x in map(''.join, zip(*[iter(hex_stream)]*2))]
    return struct.pack("!" + "B" * len(values), *values)

class BgpMessageTestCase(unittest.TestCase):
    def test_open_message_parses(self):
        serialised_message = build_byte_string("04fe0900b4c0a8000f00")
        message = parse_bgp_message(BgpMessage.OPEN_MESSAGE, serialised_message)
        self.assertEqual(message.version, 4)
        self.assertEqual(message.peer_as, 65033)
        self.assertEqual(message.hold_time, 180)
        self.assertEqual(message.identifier, 0xC0A8000F)

    def test_open_message_packs(self):
        expected_serialised_message = build_byte_string("04fe0900b4c0a8000f00")
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

    def test_update_message_parses(self):
        serialised_message = build_byte_string("0000002740010101400200400304c0a800218004040000000040050400000064c00808fe0901f4fe090258080a")
        message = parse_bgp_message(BgpMessage.UPDATE_MESSAGE, serialised_message)
        self.assertEqual(message.nlri[0], IP4Prefix(b"\x0A\x00\x00\x00", 8))
        self.assertEqual(message.path_attributes[0], "NEXT_HOP: 192.168.0.33")