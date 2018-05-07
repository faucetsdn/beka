from beeper.event import Event
from beeper.bgp_message import BgpMessage, BgpOpenMessage, BgpKeepaliveMessage, BgpNotificationMessage
from beeper.ip4 import ip_number_to_string, ip_string_to_number
from beeper.route import Route
from collections import deque

import time

class Beeper:
    DEFAULT_HOLD_TIME = 240
    DEFAULT_KEEPALIVE_TIME = DEFAULT_HOLD_TIME // 3

    def __init__(self, my_as, peer_as, my_id, peer_id, hold_time):
        self.my_as = my_as
        self.peer_as = peer_as
        self.my_id = my_id
        self.peer_id = peer_id
        self.hold_time = hold_time
        self.keepalive_time = hold_time // 3
        self.output_messages = deque()
        self.route_updates = deque()

        self.timers = {
            "hold": None,
            "keepalive": None,
        }
        self.state = "active"

    def event(self, event, tick):
        if event.type == Event.TIMER_EXPIRED:
            self.handle_timers(tick)
        elif event.type == Event.MESSAGE_RECEIVED:
            self.handle_message(event.message, tick)
        elif event.type == Event.SHUTDOWN:
            self.handle_shutdown()

    def handle_shutdown(self):
        if self.state == "open_confirm" or self.state == "established":
            notification_message = BgpNotificationMessage(6)
            self.output_messages.append(notification_message)
        self.shutdown()

    def shutdown(self):
        self.state = "idle"

    def handle_timers(self, tick):
        if self.state == "open_confirm" or self.state == "established":
            if self.timers["hold"] + self.hold_time <= tick:
                self.handle_hold_timer(tick)
            elif self.timers["keepalive"] + self.keepalive_time <= tick:
                self.handle_keepalive_timer(tick)

    def handle_hold_timer(self, tick):
        notification_message = BgpNotificationMessage(4)
        self.output_messages.append(notification_message)
        self.shutdown()

    def handle_keepalive_timer(self, tick):
        self.timers["keepalive"] = tick
        message = BgpKeepaliveMessage()
        self.output_messages.append(message)

    def handle_message(self, message, tick):# state machine
        if self.state == "active":
            self.handle_message_active_state(message, tick)
        elif self.state == "open_confirm":
            self.handle_message_open_confirm_state(message, tick)
        elif self.state == "established":
            self.handle_message_established_state(message, tick)

    def handle_message_active_state(self, message, tick):
        if message.type == BgpMessage.OPEN_MESSAGE:
            # TODO sanity check incoming open message
            open_message = BgpOpenMessage(4, self.my_as, self.hold_time, ip_string_to_number(self.my_id))
            keepalive_message = BgpKeepaliveMessage()
            self.output_messages.append(open_message)
            self.output_messages.append(keepalive_message)
            self.timers["hold"] = tick
            self.timers["keepalive"] = tick
            self.state = "open_confirm"
        else:
            self.shutdown()

    def handle_message_open_confirm_state(self, message, tick):
        if message.type == BgpMessage.KEEPALIVE_MESSAGE:
            self.timers["hold"] = tick
            self.state = "established"
        elif message.type == BgpMessage.NOTIFICATION_MESSAGE:
            self.shutdown()
        elif message.type == BgpMessage.OPEN_MESSAGE:
            notification_message = BgpNotificationMessage(6)
            self.output_messages.append(notification_message)
            self.shutdown()
        elif message.type == BgpMessage.UPDATE_MESSAGE:
            notification_message = BgpNotificationMessage(5)
            self.output_messages.append(notification_message)
            self.shutdown()

    def handle_message_established_state(self, message, tick):
        if message.type == BgpMessage.UPDATE_MESSAGE:
            self.process_route_update(message)
        elif message.type == BgpMessage.KEEPALIVE_MESSAGE:
            self.timers["hold"] = tick
        elif message.type == BgpMessage.NOTIFICATION_MESSAGE:
            self.shutdown()
        elif message.type == BgpMessage.OPEN_MESSAGE:
            notification_message = BgpNotificationMessage(6)
            self.output_messages.append(notification_message)
            self.shutdown()

    def process_route_update(self, update_message):
        for prefix in update_message.nlri:
            route = Route(prefix, update_message.path_attributes["next_hop"], update_message.path_attributes["as_path"], update_message.path_attributes["origin"])
            self.route_updates.append(route)


