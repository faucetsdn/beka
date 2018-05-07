from beeper.event import Event
from beeper.bgp_message import BgpMessage, BgpOpenMessage, BgpKeepaliveMessage
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

    def handle_timers(self, tick):
        if self.timers["hold"] + self.hold_time <= tick:
            self.handle_hold_timer(tick)

        if self.timers["keepalive"] + self.keepalive_time <= tick:
            self.handle_keepalive_timer(tick)

    def handle_hold_timer(self, tick):
        # do stuff
        # should be state check too
        self.state = "active"

    def handle_keepalive_timer(self, tick):
        # do stuff
        self.timers["keepalive"] = tick
        message = BgpKeepaliveMessage()
        self.output_messages.append(message)

    def handle_message(self, message, tick):# state machine
        if self.state == "active":
            if message.type == BgpMessage.OPEN_MESSAGE:
                # TODO sanity check incoming open message
                open_message = BgpOpenMessage(4, self.my_as, self.hold_time, ip_string_to_number(self.my_id))
                keepalive_message = BgpKeepaliveMessage()
                self.output_messages.append(open_message)
                self.output_messages.append(keepalive_message)
                self.state = "open_confirm"
        elif self.state == "open_confirm":
            if message.type == BgpMessage.KEEPALIVE_MESSAGE:
                self.state = "established"
        if message.type == BgpMessage.UPDATE_MESSAGE:
            for prefix in message.nlri:
                route = Route(prefix, message.path_attributes["next_hop"], message.path_attributes["as_path"], message.path_attributes["origin"])
                self.route_updates.append(route)

