import struct
import unittest
from unittest.mock import MagicMock

from beka.bgp_message import BgpMessage, BgpOpenMessage, BgpUpdateMessage, BgpKeepaliveMessage, BgpNotificationMessage
from beka.state_machine import StateMachine
from beka.event import EventTimerExpired, EventMessageReceived, EventShutdown
from beka.ip import IP4Prefix, IP4Address
from beka.ip import IP6Prefix, IP6Address
from beka.route import RouteAddition, RouteRemoval
from beka.error import IdleError

def build_byte_string(hex_stream):
    values = [int(x, 16) for x in map(''.join, zip(*[iter(hex_stream)]*2))]
    return struct.pack("!" + "B" * len(values), *values)

def reset_timer_if_running(timer, tick):
    if timer.running():
        timer.reset(tick)

class StateMachinePassiveActiveTestCase(unittest.TestCase):
    def setUp(self):
        self.tick = 10000
        self.open_handler = MagicMock()
        self.state_machine = StateMachine(local_as=65001, peer_as=65002, local_address="1.1.1.1", router_id="1.1.1.1", neighbor="2.2.2.2", hold_time=240, open_handler=self.open_handler)
        self.assertEqual(self.state_machine.state, "active")
        self.assertEqual(self.state_machine.output_messages.qsize(), 0)
        self.assertFalse(self.state_machine.timers["hold"].running())
        self.assertFalse(self.state_machine.timers["keepalive"].running())

    def test_shutdown_message_advances_to_idle(self):
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventShutdown(), self.tick)
        self.assertEqual(self.state_machine.state, "idle")
        self.assertTrue("Shutdown requested" in str(context.exception))

    def test_timer_expired_event_does_nothing(self):
        self.tick += 3600
        self.state_machine.event(EventTimerExpired(), self.tick)
        self.assertEqual(self.state_machine.state, "active")
        self.assertFalse(self.state_machine.timers["hold"].expired(self.tick))
        self.assertFalse(self.state_machine.timers["keepalive"].expired(self.tick))
        self.assertEqual(self.state_machine.output_messages.qsize(), 0)
        self.assertEqual(self.state_machine.route_updates.qsize(), 0)

    def test_open_message_advances_to_open_confirm_and_sets_timers(self):
        capabilities = {"multiprotocol": "ipv4-unicast"}
        message = BgpOpenMessage(4, 65002, 240, IP4Address.from_string("2.2.2.2"), capabilities)
        self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "open_confirm")
        self.assertEqual(self.state_machine.output_messages.qsize(), 2)
        self.open_handler.assert_called_with(capabilities)
        self.assertTrue(isinstance(self.state_machine.output_messages.get(), BgpOpenMessage))
        self.assertTrue(isinstance(self.state_machine.output_messages.get(), BgpKeepaliveMessage))
        self.assertTrue(self.state_machine.timers["hold"].running())
        self.assertTrue(self.state_machine.timers["keepalive"].running())

    def test_keepalive_message_advances_to_idle(self):
        message = BgpKeepaliveMessage()
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "idle")

    def test_notification_message_advances_to_idle(self):
        message = BgpNotificationMessage(0, 0, b"")
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "idle")

    def test_update_message_advances_to_idle(self):
        path_attributes = {
            "next_hop" : IP4Address.from_string("5.4.3.2"),
            "as_path" : "65032 65011 65002",
            "origin" : "EGP"
            }
        message = BgpUpdateMessage([], path_attributes, [IP4Prefix.from_string("192.168.0.0/16")])
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "idle")

class StateMachineOpenSentTestCase(unittest.TestCase):
    def setUp(self):
        self.tick = 10000
        self.open_handler = MagicMock()
        self.state_machine = StateMachine(local_as=65001, peer_as=65002, local_address="1.1.1.1", router_id="1.1.1.1", neighbor="2.2.2.2", hold_time=240, open_handler=self.open_handler)
        self.assertEqual(self.state_machine.state, "active")
        # TODO trigger this correctly
        self.state_machine.state = "open_sent"
        self.state_machine.timers["hold"].reset(self.tick)
        self.assertEqual(self.state_machine.output_messages.qsize(), 0)
        self.assertFalse(self.state_machine.timers["keepalive"].running())
        self.assertTrue(self.state_machine.timers["hold"].running())

    def test_shutdown_message_advances_to_idle(self):
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventShutdown(), self.tick)
        self.assertEqual(self.state_machine.state, "idle")
        self.assertTrue("Shutdown requested" in str(context.exception))

    def test_hold_timer_expired_event_advances_to_idle_and_sends_notification(self):
        reset_timer_if_running(self.state_machine.timers["hold"], self.tick - 3600)
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventTimerExpired(), self.tick)
        self.assertEqual(self.state_machine.state, "idle")
        self.assertEqual(self.state_machine.output_messages.qsize(), 1)
        message = self.state_machine.output_messages.get()
        self.assertEqual(message.error_code, 4) # Hold Timer Expired

    def test_keepalive_timer_expired_event_does_nothing(self):
        reset_timer_if_running(self.state_machine.timers["keepalive"], self.tick - 3600)
        self.state_machine.event(EventTimerExpired(), self.tick)
        self.assertEqual(self.state_machine.state, "open_sent")
        self.assertEqual(self.state_machine.output_messages.qsize(), 0)
        self.assertEqual(self.state_machine.route_updates.qsize(), 0)

    def test_open_message_advances_to_open_confirm_and_sets_timers(self):
        capabilities = {"multiprotocol": "ipv4-unicast"}
        message = BgpOpenMessage(4, 65002, 240, IP4Address.from_string("2.2.2.2"), capabilities)
        self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "open_confirm")
        self.assertEqual(self.state_machine.output_messages.qsize(), 1)
        self.open_handler.assert_called_with(capabilities)
        self.assertTrue(isinstance(self.state_machine.output_messages.get(), BgpKeepaliveMessage))
        self.assertTrue(self.state_machine.timers["hold"].running())
        self.assertTrue(self.state_machine.timers["keepalive"].running())

    def test_keepalive_message_advances_to_idle(self):
        message = BgpKeepaliveMessage()
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "idle")

    def test_notification_message_advances_to_idle(self):
        message = BgpNotificationMessage(0, 0, b"")
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "idle")

    def test_update_message_advances_to_idle(self):
        path_attributes = {
            "next_hop" : IP4Address.from_string("5.4.3.2"),
            "as_path" : "65032 65011 65002",
            "origin" : "EGP"
            }
        message = BgpUpdateMessage([], path_attributes, [IP4Prefix.from_string("192.168.0.0/16")])
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "idle")

class StateMachineOpenConfirmTestCase(unittest.TestCase):
    def setUp(self):
        self.tick = 10000
        self.state_machine = StateMachine(local_as=65001, peer_as=65002, local_address="1.1.1.1", router_id="1.1.1.1", neighbor="2.2.2.2", hold_time=240)
        message = BgpOpenMessage(4, 65002, 240, IP4Address.from_string("2.2.2.2"), {"multiprotocol": "ipv4-unicast"})
        self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "open_confirm")
        for _ in range(self.state_machine.output_messages.qsize()):
            self.state_machine.output_messages.get()
        self.assertTrue(self.state_machine.timers["keepalive"].running())
        self.assertTrue(self.state_machine.timers["hold"].running())

    def test_shutdown_message_advances_to_idle_and_sends_notification(self):
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventShutdown(), self.tick)
        self.assertTrue("Shutdown requested" in str(context.exception))
        self.assertEqual(self.state_machine.state, "idle")
        self.assertEqual(self.state_machine.output_messages.qsize(), 1)
        message = self.state_machine.output_messages.get()
        self.assertEqual(message.error_code, 6) # Cease

    def test_hold_timer_expired_event_advances_to_idle_and_sends_notification(self):
        reset_timer_if_running(self.state_machine.timers["hold"], self.tick - 3600)
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventTimerExpired(), self.tick)
        self.assertEqual(self.state_machine.state, "idle")
        self.assertEqual(self.state_machine.output_messages.qsize(), 1)
        message = self.state_machine.output_messages.get()
        self.assertEqual(message.error_code, 4) # Hold Timer Expired

    def test_keepalive_timer_expired_event_sends_keepalive_and_resets_keepalive_timer(self):
        reset_timer_if_running(self.state_machine.timers["keepalive"], self.tick - 3600)
        self.state_machine.event(EventTimerExpired(), self.tick)
        self.assertEqual(self.state_machine.state, "open_confirm")
        self.assertEqual(self.state_machine.output_messages.qsize(), 1)
        message = self.state_machine.output_messages.get()
        self.assertTrue(isinstance(message, BgpKeepaliveMessage))
        self.assertFalse(self.state_machine.timers["keepalive"].expired(self.tick))
        self.assertTrue(self.state_machine.timers["keepalive"].running())

    def test_notification_message_advances_to_idle(self):
        message = BgpNotificationMessage(0, 0, b"")
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "idle")

    def test_keepalive_message_advances_to_established_and_resets_hold_timer(self):
        self.tick += 3600
        message = BgpKeepaliveMessage()
        self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "established")
        self.assertTrue(self.state_machine.timers["hold"].running())
        self.assertFalse(self.state_machine.timers["hold"].expired(self.tick))

    def test_keepalive_message_sends_all_routes(self):
        self.tick += 3600
        self.state_machine.routes_to_advertise = [
            RouteAddition(
                IP4Prefix.from_string("10.0.0.0/8"),
                IP4Address.from_string("192.168.1.33"),
                "",
                "IGP"
            ),
            RouteAddition(
                IP4Prefix.from_string("192.168.64.0/23"),
                IP4Address.from_string("192.168.1.33"),
                "",
                "IGP"
            ),
            RouteAddition(
                IP4Prefix.from_string("192.168.128.0/23"),
                IP4Address.from_string("192.168.1.34"),
                "",
                "IGP"
            )
        ]
        message = BgpKeepaliveMessage()
        self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "established")
        self.assertTrue(self.state_machine.timers["hold"].running())
        self.assertFalse(self.state_machine.timers["hold"].expired(self.tick))
        self.assertEqual(self.state_machine.output_messages.qsize(), 2)
        first_update = self.state_machine.output_messages.get()
        second_update = self.state_machine.output_messages.get()
        self.assertTrue(isinstance(first_update, BgpUpdateMessage))
        self.assertTrue(isinstance(second_update, BgpUpdateMessage))
        self.assertEqual(first_update.path_attributes["next_hop"], IP4Address.from_string("192.168.1.33"))
        self.assertEqual(first_update.nlri, [
            IP4Prefix.from_string("10.0.0.0/8"),
            IP4Prefix.from_string("192.168.64.0/23")
        ])
        self.assertEqual(second_update.path_attributes["next_hop"], IP4Address.from_string("192.168.1.34"))
        self.assertEqual(second_update.nlri, [
            IP4Prefix.from_string("192.168.128.0/23")
        ])

    def test_keepalive_message_sends_all_routes_v6(self):
        self.tick += 3600
        self.state_machine.routes_to_advertise = [
            RouteAddition(
                IP6Prefix.from_string("2001:db4::/127"),
                IP6Address.from_string("2001:db1::1"),
                "",
                "IGP"
            ),
            RouteAddition(
                IP6Prefix.from_string("2001:db5::/127"),
                IP6Address.from_string("2001:db1::1"),
                "",
                "IGP"
            ),
            RouteAddition(
                IP6Prefix.from_string("2001:db6::/127"),
                IP6Address.from_string("2001:db1::2"),
                "",
                "IGP"
            )
        ]
        message = BgpKeepaliveMessage()
        self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "established")
        self.assertTrue(self.state_machine.timers["hold"].running())
        self.assertFalse(self.state_machine.timers["hold"].expired(self.tick))
        self.assertEqual(self.state_machine.output_messages.qsize(), 2)
        first_update = self.state_machine.output_messages.get()
        second_update = self.state_machine.output_messages.get()
        self.assertTrue(isinstance(first_update, BgpUpdateMessage))
        self.assertTrue(isinstance(second_update, BgpUpdateMessage))
        self.assertEqual(first_update.path_attributes["mp_reach_nlri"]["next_hop"], [IP6Address.from_string("2001:db1::1")])
        self.assertEqual(first_update.path_attributes["mp_reach_nlri"]["nlri"], [
            IP6Prefix.from_string("2001:db4::/127"),
            IP6Prefix.from_string("2001:db5::/127")
        ])
        self.assertEqual(second_update.path_attributes["mp_reach_nlri"]["next_hop"], [IP6Address.from_string("2001:db1::2")])
        self.assertEqual(second_update.path_attributes["mp_reach_nlri"]["nlri"], [
            IP6Prefix.from_string("2001:db6::/127")
        ])

    def test_open_message_advances_to_idle_and_sends_notification(self):
        message = BgpOpenMessage(4, 65002, 240, IP4Address.from_string("2.2.2.2"), {"multiprotocol": "ipv4-unicast"})
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "idle")
        self.assertEqual(self.state_machine.output_messages.qsize(), 1)
        message = self.state_machine.output_messages.get()
        self.assertEqual(message.error_code, 6) # Cease

    def test_update_message_advances_to_idle(self):
        path_attributes = {
            "next_hop" : IP4Address.from_string("5.4.3.2"),
            "as_path" : "65032 65011 65002",
            "origin" : "EGP"
            }
        message = BgpUpdateMessage([], path_attributes, [IP4Prefix.from_string("192.168.0.0/16")])
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "idle")
        self.assertEqual(self.state_machine.output_messages.qsize(), 1)
        message = self.state_machine.output_messages.get()
        self.assertEqual(message.error_code, 5) # FSM error

class StateMachineEstablishedTestCase(unittest.TestCase):
    def setUp(self):
        self.tick = 10000
        self.state_machine = StateMachine(local_as=65001, peer_as=65002, local_address="1.1.1.1", router_id="1.1.1.1", neighbor="2.2.2.2", hold_time=240)
        message = BgpOpenMessage(4, 65002, 240, IP4Address.from_string("2.2.2.2"), {"multiprotocol": "ipv4-unicast"})
        self.state_machine.event(EventMessageReceived(message), self.tick)
        for _ in range(self.state_machine.output_messages.qsize()):
            self.state_machine.output_messages.get()
        message = BgpKeepaliveMessage()
        self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "established")
        self.assertTrue(self.state_machine.timers["hold"].running())
        self.assertTrue(self.state_machine.timers["keepalive"].running())

    def test_keepalive_timer_expired_event_sends_keepalive_and_resets_keepalive_timer(self):
        reset_timer_if_running(self.state_machine.timers["keepalive"], self.tick - 3600)
        self.state_machine.event(EventTimerExpired(), self.tick)
        self.assertEqual(self.state_machine.state, "established")
        self.assertEqual(self.state_machine.output_messages.qsize(), 1)
        message = self.state_machine.output_messages.get()
        self.assertTrue(isinstance(message, BgpKeepaliveMessage))
        self.assertTrue(self.state_machine.timers["keepalive"].running())
        self.assertFalse(self.state_machine.timers["keepalive"].expired(self.tick))

    def test_update_message_adds_route(self):
        path_attributes = {
            "next_hop" : IP4Address.from_string("5.4.3.2"),
            "as_path" : "65032 65011 65002",
            "origin" : "EGP"
        }
        route_attributes = {
            "prefix" : IP4Prefix.from_string("192.168.0.0/16"),
            "next_hop" : IP4Address.from_string("5.4.3.2"),
            "as_path" : "65032 65011 65002",
            "origin" : "EGP"
        }
        message = BgpUpdateMessage([], path_attributes, [IP4Prefix.from_string("192.168.0.0/16")])
        self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "established")
        self.assertEqual(self.state_machine.route_updates.qsize(), 1)
        self.assertEqual(self.state_machine.route_updates.get(), RouteAddition(**route_attributes))

    def test_update_message_removes_route(self):
        message = BgpUpdateMessage([IP4Prefix.from_string("192.168.0.0/16")], [], [])
        self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "established")
        self.assertEqual(self.state_machine.route_updates.qsize(), 1)
        self.assertEqual(self.state_machine.route_updates.get(), RouteRemoval(IP4Prefix.from_string("192.168.0.0/16")))

    def test_update_v6_message_adds_route(self):
        path_attributes = {
            "as_path" : "65032 65011 65002",
            "origin" : "EGP",
            "mp_reach_nlri" : {
                "next_hop" : [
                    IP6Address.from_string("2001:db8:1::242:ac11:2"),
                    IP6Address.from_string("fe80::42:acff:fe11:2"),
                ],
                "nlri" : [
                    IP6Prefix.from_string("2001:db4::/127"),
                ]
            }
        }
        route_attributes = {
            "prefix" : IP6Prefix.from_string("2001:db4::/127"),
            "next_hop" : IP6Address.from_string("2001:db8:1::242:ac11:2"),
            "as_path" : "65032 65011 65002",
            "origin" : "EGP"
        }
        message = BgpUpdateMessage([], path_attributes, [])
        self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "established")
        self.assertEqual(self.state_machine.route_updates.qsize(), 1)
        self.assertEqual(self.state_machine.route_updates.get(), RouteAddition(**route_attributes))

    def test_shutdown_message_advances_to_idle_and_sends_notification(self):
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventShutdown(), self.tick)
        self.assertTrue("Shutdown requested" in str(context.exception))
        self.assertEqual(self.state_machine.state, "idle")
        self.assertEqual(self.state_machine.output_messages.qsize(), 1)
        message = self.state_machine.output_messages.get()
        self.assertEqual(message.error_code, 6) # Cease

    def test_hold_timer_expired_event_advances_to_idle_and_sends_notification(self):
        reset_timer_if_running(self.state_machine.timers["hold"], self.tick - 3600)
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventTimerExpired(), self.tick)
        self.assertEqual(self.state_machine.state, "idle")
        self.assertEqual(self.state_machine.output_messages.qsize(), 1)
        message = self.state_machine.output_messages.get()
        self.assertEqual(message.error_code, 4) # Hold Timer Expired

    def test_notification_message_advances_to_idle(self):
        message = BgpNotificationMessage(0, 0, b"")
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "idle")

    def test_open_message_advances_to_idle_and_sends_notification(self):
        message = BgpOpenMessage(4, 65002, 240, IP4Address.from_string("2.2.2.2"), {"multiprotocol": "ipv4-unicast"})
        with self.assertRaises(IdleError) as context:
            self.state_machine.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.state_machine.state, "idle")
        self.assertEqual(self.state_machine.output_messages.qsize(), 1)
        message = self.state_machine.output_messages.get()
        self.assertEqual(message.error_code, 6) # Cease
