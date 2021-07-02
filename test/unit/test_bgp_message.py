import struct
import unittest

from beka.bgp_message import BgpMessage, BgpMessageParser, BgpMessagePacker, BgpOpenMessage
from beka.bgp_message import BgpUpdateMessage, BgpNotificationMessage, BgpKeepaliveMessage
from beka.ip import IP4Prefix, IP4Address
from beka.ip import IP6Prefix, IP6Address

def build_byte_string(hex_stream):
    values = [int(x, 16) for x in map(''.join, zip(*[iter(hex_stream)]*2))]
    return struct.pack("!" + "B" * len(values), *values)

class BgpMessageTestCase(unittest.TestCase):
    def test_open_message_parses_ipv4_multiprotocol(self):
        serialised_message = build_byte_string("04fe0900b4c0a8000f080206010400010001")
        message = BgpMessageParser().parse(BgpMessage.OPEN_MESSAGE, serialised_message)
        self.assertEqual(message.version, 4)
        self.assertEqual(message.peer_as, 65033)
        self.assertEqual(message.hold_time, 180)
        self.assertEqual(message.identifier, IP4Address.from_string("192.168.0.15"))
        self.assertEqual(message.capabilities["multiprotocol"], ["ipv4-unicast"])

    def test_open_message_parses_ipv6_multiprotocol(self):
        serialised_message = build_byte_string("04fe0900b4c0a8000f080206010400020001")
        message = BgpMessageParser().parse(BgpMessage.OPEN_MESSAGE, serialised_message)
        self.assertEqual(message.version, 4)
        self.assertEqual(message.peer_as, 65033)
        self.assertEqual(message.hold_time, 180)
        self.assertEqual(message.identifier, IP4Address.from_string("192.168.0.15"))
        self.assertEqual(message.capabilities["multiprotocol"], ["ipv6-unicast"])

    def test_open_message_parses_multiprotocol_4_byte_asn(self):
        serialised_message = build_byte_string("04fe0900b4c0a8000f0e020c01040001000141040000fdeb")
        message = BgpMessageParser().parse(BgpMessage.OPEN_MESSAGE, serialised_message)
        self.assertEqual(message.version, 4)
        self.assertEqual(message.peer_as, 65033)
        self.assertEqual(message.hold_time, 180)
        self.assertEqual(message.identifier, IP4Address.from_string("192.168.0.15"))
        self.assertEqual(message.capabilities["multiprotocol"], ["ipv4-unicast"])
        self.assertEqual(message.capabilities["fourbyteas"], [65003])

    def test_open_message_parses_route_refresh(self):
        serialised_message = build_byte_string("04fe0900b4c0a8000f0a02080104000200010200")
        message = BgpMessageParser().parse(BgpMessage.OPEN_MESSAGE, serialised_message)
        self.assertEqual(message.version, 4)
        self.assertEqual(message.peer_as, 65033)
        self.assertEqual(message.hold_time, 180)
        self.assertEqual(message.identifier, IP4Address.from_string("192.168.0.15"))
        self.assertEqual(message.capabilities["multiprotocol"], ["ipv6-unicast"])
        self.assertEqual(message.capabilities["routerefresh"], [True])

    def test_open_message_parses_exabgp_optional_params(self):
        serialised_message = build_byte_string("04fe0900b4c0a8000f9402060104000100010206010400010002020601040001000402060104000100800206010400010084020601040001008502060104000100860206010400020001020601040002000202060104000200040206010400020080020601040002008502060104000200860206010400190041020601040019004602060104400400470206010440040048020206000206410400010001")
        message = BgpMessageParser().parse(BgpMessage.OPEN_MESSAGE, serialised_message)
        self.assertEqual(message.version, 4)
        self.assertEqual(message.peer_as, 65033)
        self.assertEqual(message.hold_time, 180)
        self.assertEqual(message.identifier, IP4Address.from_string("192.168.0.15"))
        self.assertTrue("ipv4-unicast" in message.capabilities["multiprotocol"])
        self.assertTrue("ipv6-unicast" in message.capabilities["multiprotocol"])

    def test_open_message_packs(self):
        expected_serialised_message = build_byte_string("04fe0900b4c0a8000f080206010400010001")
        message = BgpOpenMessage(
            4, 65033, 180,
            IP4Address.from_string("192.168.0.15"),
            {"multiprotocol": ["ipv4-unicast"]}
        )
        serialised_message = BgpMessagePacker().pack(message)
        self.assertEqual(serialised_message[19:], expected_serialised_message)

    def test_open_message_packs_capabilities(self):
        expected_serialised_message = build_byte_string("04fe0900b4c0a8000f160214010400010001010400020001020041040000fdeb")
        capabilities = {
            "multiprotocol": ["ipv4-unicast", "ipv6-unicast"],
            "routerefresh": [True],
            "fourbyteas": [65003]
        }
        message = BgpOpenMessage(
            4, 65033, 180,
            IP4Address.from_string("192.168.0.15"),
            capabilities
        )
        serialised_message = BgpMessagePacker().pack(message)
        self.assertEqual(serialised_message[19:], expected_serialised_message)

    def test_keepalive_message_parses(self):
        serialised_message = b""
        message = BgpMessageParser().parse(BgpMessage.KEEPALIVE_MESSAGE, serialised_message)

    def test_keepalive_message_packs(self):
        expected_serialised_message = b""
        message = BgpKeepaliveMessage()
        serialised_message = BgpMessagePacker().pack(message)
        self.assertEqual(serialised_message[19:], expected_serialised_message)

    def test_notification_message_parses(self):
        serialised_message = build_byte_string("0202feb0")
        message = BgpMessageParser().parse(BgpMessage.NOTIFICATION_MESSAGE, serialised_message)
        self.assertEqual(message.error_code, 2)
        self.assertEqual(message.error_subcode, 2)
        self.assertEqual(message.data, b"\xfe\xb0")

    def test_notification_message_packs(self):
        expected_serialised_message = build_byte_string("0202feb0")
        message = BgpNotificationMessage(2, 2, b"\xfe\xb0")
        serialised_message = BgpMessagePacker().pack(message)
        self.assertEqual(serialised_message[19:], expected_serialised_message)

    def test_update_message_new_routes_parses(self):
        serialised_message = build_byte_string("0000000e40010101400200400304c0a80021080a")
        message = BgpMessageParser().parse(BgpMessage.UPDATE_MESSAGE, serialised_message)
        self.assertEqual(message.nlri[0], IP4Prefix.from_string("10.0.0.0/8"))
        self.assertEqual(
            message.path_attributes["next_hop"],
            IP4Address.from_string("192.168.0.33")
        )
        self.assertEqual(message.path_attributes["origin"], "EGP")
        self.assertEqual(message.path_attributes["as_path"], "")

    def test_update_message_new_routes_packs(self):
        expected_serialised_message = build_byte_string("0000000e40010101400200400304c0a80021080a17c0a840")
        nlri = [
            IP4Prefix.from_string("10.0.0.0/8"),
            IP4Prefix.from_string("192.168.64.0/23")
        ]
        path_attributes = {
            "next_hop": IP4Address.from_string("192.168.0.33"),
            "origin": "EGP",
            "as_path": ""
        }
        message = BgpUpdateMessage([], path_attributes, nlri)
        serialised_message = BgpMessagePacker().pack(message)
        self.assertEqual(serialised_message[19:], expected_serialised_message)

    def test_update_message_new_routes_parses_as4(self):
        serialised_message = build_byte_string("000000274001010040020802035ba0fe08fdebc0110e020300bc614e0000fe080000fdeb400304ac1900042009090909")
        message = BgpMessageParser().parse(BgpMessage.UPDATE_MESSAGE, serialised_message)
        self.assertEqual(message.nlri, [IP4Prefix.from_string("9.9.9.9/32")])
        self.assertEqual(message.path_attributes["next_hop"], IP4Address.from_string("172.25.0.4"))
        self.assertEqual(message.path_attributes["origin"], "IGP")
        self.assertEqual(message.path_attributes["as_path"], "23456 65032 65003")
        self.assertEqual(message.path_attributes["as4_path"], "12345678 65032 65003")

    def test_update_message_new_routes_packs_as4(self):
        expected_serialised_message = build_byte_string("000000274001010040020802035ba0fe08fdebc0110e020300bc614e0000fe080000fdeb400304ac1900042009090909")
        nlri = [
            IP4Prefix.from_string("9.9.9.9/32"),
        ]
        path_attributes = {
            "next_hop": IP4Address.from_string("172.25.0.4"),
            "origin": "IGP",
            "as_path": "23456 65032 65003",
            "as4_path": "12345678 65032 65003"
        }
        message = BgpUpdateMessage([], path_attributes, nlri)
        serialised_message = BgpMessagePacker().pack(message)
        self.assertEqual(serialised_message[19:], expected_serialised_message)

    def test_update_message_new_routes_parses_as4_new(self):
        serialised_message = build_byte_string("0000001c4001010040020e020300bc614e0000fe080001b2e5400304ac1900042009090909")
        parser = BgpMessageParser()
        parser.capabilities = {
            "fourbyteas": 12345
        }
        message = parser.parse(BgpMessage.UPDATE_MESSAGE, serialised_message)
        self.assertEqual(message.nlri, [IP4Prefix.from_string("9.9.9.9/32")])
        self.assertEqual(message.path_attributes["next_hop"], IP4Address.from_string("172.25.0.4"))
        self.assertEqual(message.path_attributes["origin"], "IGP")
        self.assertEqual(message.path_attributes["as_path"], "12345678 65032 111333")

    def test_update_message_new_routes_packs_as4_new(self):
        expected_serialised_message = build_byte_string("0000001c4001010040020e020300bc614e0000fe080001b2e5400304ac1900042009090909")
        nlri = [
            IP4Prefix.from_string("9.9.9.9/32"),
        ]
        path_attributes = {
            "next_hop": IP4Address.from_string("172.25.0.4"),
            "origin": "IGP",
            "as_path": "12345678 65032 111333"
        }
        message = BgpUpdateMessage([], path_attributes, nlri)
        packer = BgpMessagePacker()
        packer.capabilities = {"fourbyteas": 12345}
        serialised_message = packer.pack(message)
        self.assertEqual(serialised_message[19:], expected_serialised_message)

    def test_update_message_withdrawn_routes_parses(self):
        serialised_message = build_byte_string("0004180a01010000")
        message = BgpMessageParser().parse(BgpMessage.UPDATE_MESSAGE, serialised_message)
        self.assertEqual(message.withdrawn_routes[0], IP4Prefix.from_string("10.1.1.0/24"))

    def test_update_message_withdrawn_routes_packs(self):
        expected_serialised_message = build_byte_string("0004180a01010000")
        message = BgpUpdateMessage([IP4Prefix.from_string("10.1.1.0/24")], {}, [])
        serialised_message = BgpMessagePacker().pack(message)
        self.assertEqual(serialised_message[19:], expected_serialised_message)

    def test_update_v6_message_new_routes_parses(self):
        serialised_message = build_byte_string("0000004b400101004002040201fdeb800e3d0002012020010db80001000000000242ac110002fe800000000000000042acfffe110002007f20010db40000000000000000000000002f20010db30000")
        message = BgpMessageParser().parse(BgpMessage.UPDATE_MESSAGE, serialised_message)
        self.assertEqual(message.path_attributes["origin"], "IGP")
        self.assertEqual(
            message.path_attributes["mp_reach_nlri"]["next_hop"][0],
            IP6Address.from_string("2001:db8:1::242:ac11:2")
        )
        self.assertEqual(
            message.path_attributes["mp_reach_nlri"]["next_hop"][1],
            IP6Address.from_string("fe80::42:acff:fe11:2")
        )
        self.assertEqual(
            message.path_attributes["mp_reach_nlri"]["nlri"][0],
            IP6Prefix.from_string("2001:db4::/127")
        )
        self.assertEqual(
            message.path_attributes["mp_reach_nlri"]["nlri"][1],
            IP6Prefix.from_string("2001:db3::/47")
        )

    def test_update_v6_message_withdrawn_routes_parses(self):
        serialised_message = build_byte_string("0000002d800f2a0002017f20010db40000000000000000000000003020010db100003320010db20000002f20010db30000")
        message = BgpMessageParser().parse(BgpMessage.UPDATE_MESSAGE, serialised_message)

        expected_withdrawn_routes = [
            IP6Prefix.from_string("2001:db4::/127"),
            IP6Prefix.from_string("2001:db1::/48"),
            IP6Prefix.from_string("2001:db2::/51"),
            IP6Prefix.from_string("2001:db3::/47")
        ]

        self.assertEqual(message.path_attributes["mp_unreach_nlri"]["withdrawn_routes"], expected_withdrawn_routes)

    def test_update_v6_message_withdrawn_routes_packs(self):
        expected_serialised_message = build_byte_string("0000002d800f2a0002017f20010db40000000000000000000000003020010db100003320010db20000002f20010db30000")

        path_attributes = {
            "mp_unreach_nlri": {
                "withdrawn_routes": [
                    IP6Prefix.from_string("2001:db4::/127"),
                    IP6Prefix.from_string("2001:db1::/48"),
                    IP6Prefix.from_string("2001:db2::/51"),
                    IP6Prefix.from_string("2001:db3::/47")
                ]
            }
        }

        message = BgpUpdateMessage([], path_attributes, [])
        serialised_message = BgpMessagePacker().pack(message)
        self.assertEqual(serialised_message[19:], expected_serialised_message)

    def test_update_v6_message_new_routes_packs(self):
        expected_serialised_message = build_byte_string("0000004740010100400200800e3d0002012020010db80001000000000242ac110002fe800000000000000042acfffe110002007f20010db40000000000000000000000002f20010db30000")
        path_attributes = {
            "origin": "IGP",
            "as_path": "",
            "mp_reach_nlri": {
                "next_hop": [
                    IP6Address.from_string("2001:db8:1::242:ac11:2"),
                    IP6Address.from_string("fe80::42:acff:fe11:2")
                ],
                "nlri": [
                    IP6Prefix.from_string("2001:db4::/127"),
                    IP6Prefix.from_string("2001:db3::/47")
                ]
            }
        }
        message = BgpUpdateMessage([], path_attributes, [])
        serialised_message = BgpMessagePacker().pack(message)
        self.assertEqual(serialised_message[19:], expected_serialised_message)
