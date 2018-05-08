from beeper.bgp_message import BgpMessage, BgpOpenMessage, BgpUpdateMessage, BgpKeepaliveMessage, BgpNotificationMessage
from beeper.beeper import Beeper
from beeper.event import Event, EventTimerExpired, EventMessageReceived, EventShutdown
from beeper.ip4 import ip_string_to_number, IP4Prefix
from beeper.route import Route

import time
import unittest

class BeeperPassiveActiveTestCase(unittest.TestCase):
    def setUp(self):
        self.tick = 10000
        self.beeper = Beeper(my_as=65001, peer_as=65002, my_id="1.1.1.1", peer_id="2.2.2.2", hold_time=240)
        self.old_hold_timer = self.beeper.timers["hold"]
        self.old_keepalive_timer = self.beeper.timers["keepalive"]
        self.assertEqual(self.beeper.state, "active")
        self.assertEqual(self.beeper.output_messages.qsize(), 0)

    def test_shutdown_message_advances_to_idle(self):
        self.beeper.event(EventShutdown(), self.tick)
        self.assertEqual(self.beeper.state, "idle")

    def test_timer_expired_event_does_nothing(self):
        self.tick += 3600
        self.beeper.event(EventTimerExpired(), self.tick)
        self.assertEqual(self.beeper.state, "active")
        self.assertEqual(self.old_hold_timer, self.beeper.timers["hold"])
        self.assertEqual(self.old_keepalive_timer, self.beeper.timers["keepalive"])
        self.assertEqual(self.beeper.output_messages.qsize(), 0)
        self.assertEqual(self.beeper.route_updates.qsize(), 0)

    def test_open_message_advances_to_open_confirm_and_sets_timers(self):
        message = BgpOpenMessage(4, 65002, 240, ip_string_to_number("2.2.2.2"))
        self.beeper.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.beeper.state, "open_confirm")
        self.assertEqual(self.beeper.output_messages.qsize(), 2)
        self.assertEqual(self.beeper.output_messages.get().type, BgpMessage.OPEN_MESSAGE)
        self.assertEqual(self.beeper.output_messages.get().type, BgpMessage.KEEPALIVE_MESSAGE)
        self.assertEqual(self.beeper.timers["hold"], self.tick)
        self.assertEqual(self.beeper.timers["keepalive"], self.tick)

    def test_keepalive_message_advances_to_idle(self):
        message = BgpKeepaliveMessage()
        self.beeper.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.beeper.state, "idle")

    def test_notification_message_advances_to_idle(self):
        message = BgpNotificationMessage(0, 0, b"")
        self.beeper.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.beeper.state, "idle")

    def test_update_message_advances_to_idle(self):
        path_attributes = {
            "next_hop" : "5.4.3.2",
            "as_path" : "65032 65011 65002",
            "origin" : "EGP"
            }
        message = BgpUpdateMessage([], path_attributes, [IP4Prefix("192.168.0.0", 16)])
        self.beeper.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.beeper.state, "idle")

class BeeperOpenConfirmTestCase(unittest.TestCase):
    def setUp(self):
        self.tick = 10000
        self.beeper = Beeper(my_as=65001, peer_as=65002, my_id="1.1.1.1", peer_id="2.2.2.2", hold_time=240)
        message = BgpOpenMessage(4, 65002, 240, ip_string_to_number("2.2.2.2"))
        self.beeper.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.beeper.state, "open_confirm")
        for _ in range(self.beeper.output_messages.qsize()):
            self.beeper.output_messages.get()
        self.old_hold_timer = self.beeper.timers["hold"]
        self.old_keepalive_timer = self.beeper.timers["keepalive"]

    def test_shutdown_message_advances_to_idle_and_sends_notification(self):
        self.beeper.event(EventShutdown(), self.tick)
        self.assertEqual(self.beeper.state, "idle")
        self.assertEqual(self.beeper.output_messages.qsize(), 1)
        message = self.beeper.output_messages.get()
        self.assertEqual(message.type, BgpMessage.NOTIFICATION_MESSAGE)
        self.assertEqual(message.error_code, 6) # Cease

    def test_hold_timer_expired_event_advances_to_idle_and_sends_notification(self):
        self.tick = self.old_hold_timer
        self.beeper.timers["hold"] = self.tick - 3600
        self.beeper.event(EventTimerExpired(), self.tick)
        self.assertEqual(self.beeper.state, "idle")
        self.assertEqual(self.beeper.output_messages.qsize(), 1)
        message = self.beeper.output_messages.get()
        self.assertEqual(message.type, BgpMessage.NOTIFICATION_MESSAGE)
        self.assertEqual(message.error_code, 4) # Hold Timer Expired

    def test_keepalive_timer_expired_event_sends_keepalive_and_resets_keepalive_timer(self):
        self.beeper.timers["keepalive"] = self.tick - 3600
        self.beeper.event(EventTimerExpired(), self.tick)
        self.assertEqual(self.beeper.state, "open_confirm")
        self.assertEqual(self.beeper.output_messages.qsize(), 1)
        message = self.beeper.output_messages.get()
        self.assertEqual(message.type, BgpMessage.KEEPALIVE_MESSAGE)
        self.assertEqual(self.beeper.timers["keepalive"], self.tick)

    def test_notification_message_advances_to_idle(self):
        message = BgpNotificationMessage(0, 0, b"")
        self.beeper.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.beeper.state, "idle")

    def test_keepalive_message_advances_to_established_and_resets_hold_timer(self):
        self.tick += 3600
        message = BgpKeepaliveMessage()
        self.beeper.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.beeper.state, "established")
        self.assertEqual(self.beeper.timers["hold"], self.tick)

    def test_open_message_advances_to_idle_and_sends_notification(self):
        message = BgpOpenMessage(4, 65002, 240, ip_string_to_number("2.2.2.2"))
        self.beeper.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.beeper.state, "idle")
        self.assertEqual(self.beeper.output_messages.qsize(), 1)
        message = self.beeper.output_messages.get()
        self.assertEqual(message.type, BgpMessage.NOTIFICATION_MESSAGE)
        self.assertEqual(message.error_code, 6) # Cease

    def test_update_message_advances_to_idle(self):
        path_attributes = {
            "next_hop" : "5.4.3.2",
            "as_path" : "65032 65011 65002",
            "origin" : "EGP"
            }
        message = BgpUpdateMessage([], path_attributes, [IP4Prefix("192.168.0.0", 16)])
        self.beeper.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.beeper.state, "idle")
        self.assertEqual(self.beeper.output_messages.qsize(), 1)
        message = self.beeper.output_messages.get()
        self.assertEqual(message.type, BgpMessage.NOTIFICATION_MESSAGE)
        self.assertEqual(message.error_code, 5) # FSM error

class BeeperEstablishedTestCase(unittest.TestCase):
    def setUp(self):
        self.tick = 10000
        self.beeper = Beeper(my_as=65001, peer_as=65002, my_id="1.1.1.1", peer_id="2.2.2.2", hold_time=240)
        message = BgpOpenMessage(4, 65002, 240, ip_string_to_number("2.2.2.2"))
        self.beeper.event(EventMessageReceived(message), self.tick)
        for _ in range(self.beeper.output_messages.qsize()):
            self.beeper.output_messages.get()
        message = BgpKeepaliveMessage()
        self.beeper.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.beeper.state, "established")
        self.old_hold_timer = self.beeper.timers["hold"]
        self.old_keepalive_timer = self.beeper.timers["keepalive"]

    def test_keepalive_timer_expired_event_sends_keepalive_and_resets_keepalive_timer(self):
        self.beeper.timers["keepalive"] = self.tick - 3600
        self.beeper.event(EventTimerExpired(), self.tick)
        self.assertEqual(self.beeper.state, "established")
        self.assertEqual(self.beeper.output_messages.qsize(), 1)
        message = self.beeper.output_messages.get()
        self.assertEqual(message.type, BgpMessage.KEEPALIVE_MESSAGE)
        self.assertEqual(self.beeper.timers["keepalive"], self.tick)

    def test_update_message_adds_route(self):
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
        self.beeper.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.beeper.state, "established")
        self.assertEqual(self.beeper.route_updates.qsize(), 1)
        self.assertEqual(self.beeper.route_updates.get(), Route(**route_attributes))

    def test_shutdown_message_advances_to_idle_and_sends_notification(self):
        self.beeper.event(EventShutdown(), self.tick)
        self.assertEqual(self.beeper.state, "idle")
        self.assertEqual(self.beeper.output_messages.qsize(), 1)
        message = self.beeper.output_messages.get()
        self.assertEqual(message.type, BgpMessage.NOTIFICATION_MESSAGE)
        self.assertEqual(message.error_code, 6) # Cease

    def test_hold_timer_expired_event_advances_to_idle_and_sends_notification(self):
        self.tick = self.old_hold_timer
        self.beeper.timers["hold"] = self.tick - 3600
        self.beeper.event(EventTimerExpired(), self.tick)
        self.assertEqual(self.beeper.state, "idle")
        self.assertEqual(self.beeper.output_messages.qsize(), 1)
        message = self.beeper.output_messages.get()
        self.assertEqual(message.type, BgpMessage.NOTIFICATION_MESSAGE)
        self.assertEqual(message.error_code, 4) # Hold Timer Expired

    def test_notification_message_advances_to_idle(self):
        message = BgpNotificationMessage(0, 0, b"")
        self.beeper.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.beeper.state, "idle")

    def test_open_message_advances_to_idle_and_sends_notification(self):
        message = BgpOpenMessage(4, 65002, 240, ip_string_to_number("2.2.2.2"))
        self.beeper.event(EventMessageReceived(message), self.tick)
        self.assertEqual(self.beeper.state, "idle")
        self.assertEqual(self.beeper.output_messages.qsize(), 1)
        message = self.beeper.output_messages.get()
        self.assertEqual(message.type, BgpMessage.NOTIFICATION_MESSAGE)
        self.assertEqual(message.error_code, 6) # Cease
