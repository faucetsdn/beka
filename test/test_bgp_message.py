from beeper.bgp_message import BgpMessage, parse_bgp_message, BgpOpenMessage, BgpNotificationMessage, BgpKeepaliveMessage
from beeper.ip4 import IP4Prefix, IP4Address
from beeper.ip6 import IP6Prefix, IP6Address
import socket
import struct
import unittest

def build_byte_string(hex_stream):
    values = [int(x, 16) for x in map(''.join, zip(*[iter(hex_stream)]*2))]
    return struct.pack("!" + "B" * len(values), *values)

class BgpMessageTestCase(unittest.TestCase):
    def test_open_message_parses(self):
        serialised_message = build_byte_string("04fe0900b4c0a8000f080206010400020001")
        message = parse_bgp_message(BgpMessage.OPEN_MESSAGE, serialised_message)
        self.assertEqual(message.version, 4)
        self.assertEqual(message.peer_as, 65033)
        self.assertEqual(message.hold_time, 180)
        self.assertEqual(message.identifier, IP4Address.from_string("192.168.0.15"))
        self.assertEqual(message.capabilities, build_byte_string("010400020001"))

    def test_open_message_packs(self):
        expected_serialised_message = build_byte_string("04fe0900b4c0a8000f080206010400020001")
        message = BgpOpenMessage(4, 65033, 180, IP4Address.from_string("192.168.0.15"), build_byte_string("010400020001"))
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

    def test_notification_message_parses(self):
        serialised_message = build_byte_string("0202feb0")
        message = parse_bgp_message(BgpMessage.NOTIFICATION_MESSAGE, serialised_message)
        self.assertEqual(message.error_code, 2)
        self.assertEqual(message.error_subcode, 2)
        self.assertEqual(message.data, b"\xfe\xb0")

    def test_notification_message_packs(self):
        expected_serialised_message = build_byte_string("0202feb0")
        message = BgpNotificationMessage(2, 2, b"\xfe\xb0")
        serialised_message = message.pack()
        self.assertEqual(serialised_message, expected_serialised_message)

    def test_update_message_new_routes_parses(self):
        serialised_message = build_byte_string("0000002740010101400200400304c0a800218004040000000040050400000064c00808fe0901f4fe090258080a")
        message = parse_bgp_message(BgpMessage.UPDATE_MESSAGE, serialised_message)
        self.assertEqual(message.nlri[0], IP4Prefix.from_string("10.0.0.0/8"))
        self.assertEqual(message.path_attributes["next_hop"], IP4Address.from_string("192.168.0.33"))
        self.assertEqual(message.path_attributes["origin"], "EGP")

    def test_update_message_withdrawn_routes_parses(self):
        serialised_message = build_byte_string("0004180a01010000")
        message = parse_bgp_message(BgpMessage.UPDATE_MESSAGE, serialised_message)
        self.assertEqual(message.withdrawn_routes[0], IP4Prefix.from_string("10.1.1.0/24"))

    def test_update_v6_message_new_routes_parses(self):
        serialised_message = build_byte_string("0000004b400101004002040201fdeb800e3d0002012020010db80001000000000242ac110002fe800000000000000042acfffe110002007f20010db40000000000000000000000002f20010db30000")
        message = parse_bgp_message(BgpMessage.UPDATE_MESSAGE, serialised_message)
        self.assertEqual(message.path_attributes["origin"], "IGP")
        self.assertEqual(message.path_attributes["mp_reach_nlri"]["next_hop"]["afi"], IP6Address.from_string("2001:db8:1::242:ac11:2"))
        self.assertEqual(message.path_attributes["mp_reach_nlri"]["next_hop"]["safi"], IP6Address.from_string("fe80::42:acff:fe11:2"))
        self.assertEqual(message.path_attributes["mp_reach_nlri"]["nlri"][0], IP6Prefix.from_string("2001:db4::/127"))
        self.assertEqual(message.path_attributes["mp_reach_nlri"]["nlri"][1], IP6Prefix.from_string("2001:db3::/47"))

    def test_update_v6_message_withdrawn_routes_parses(self):
        serialised_message = build_byte_string("0000002d800f2a0002017f20010db40000000000000000000000003020010db100003320010db20000002f20010db30000")
        message = parse_bgp_message(BgpMessage.UPDATE_MESSAGE, serialised_message)

        expected_withdrawn_routes = [
            IP6Prefix.from_string("2001:db4::/127"),
            IP6Prefix.from_string("2001:db1::/48"),
            IP6Prefix.from_string("2001:db2::/51"),
            IP6Prefix.from_string("2001:db3::/47")
        ]

        self.assertEqual(message.path_attributes["mp_unreach_nlri"]["withdrawn_routes"], expected_withdrawn_routes)

