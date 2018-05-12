from eventlet.queue import Queue

from .event import Event
from .bgp_message import BgpMessage, BgpOpenMessage
from .bgp_message import BgpKeepaliveMessage, BgpNotificationMessage
from .route import RouteAddition, RouteRemoval
from .ip import IPAddress

class StateMachine:
    DEFAULT_HOLD_TIME = 240
    DEFAULT_KEEPALIVE_TIME = DEFAULT_HOLD_TIME // 3

    def __init__(self, local_as, peer_as, router_id, local_address, neighbor, hold_time=DEFAULT_HOLD_TIME):
        self.local_as = local_as
        self.peer_as = peer_as
        self.router_id = IPAddress.from_string(router_id)
        self.local_address = IPAddress.from_string(local_address)
        self.neighbor = IPAddress.from_string(neighbor)
        self.hold_time = hold_time
        self.keepalive_time = hold_time // 3
        self.output_messages = Queue()
        self.route_updates = Queue()

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
            notification_message = BgpNotificationMessage(BgpNotificationMessage.CEASE)
            self.output_messages.put(notification_message)
        self.shutdown()

    def shutdown(self):
        self.state = "idle"

    def handle_timers(self, tick):
        if self.state == "open_confirm" or self.state == "established":
            if self.timers["hold"] + self.hold_time <= tick:
                self.handle_hold_timer()
            elif self.timers["keepalive"] + self.keepalive_time <= tick:
                self.handle_keepalive_timer(tick)

    def handle_hold_timer(self):
        notification_message = BgpNotificationMessage(BgpNotificationMessage.HOLD_TIMER_EXPIRED)
        self.output_messages.put(notification_message)
        self.shutdown()

    def handle_keepalive_timer(self, tick):
        self.timers["keepalive"] = tick
        message = BgpKeepaliveMessage()
        self.output_messages.put(message)

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
            open_message = BgpOpenMessage(4, self.local_as, self.hold_time, self.router_id)
            keepalive_message = BgpKeepaliveMessage()
            self.output_messages.put(open_message)
            self.output_messages.put(keepalive_message)
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
            notification_message = BgpNotificationMessage(BgpNotificationMessage.CEASE)
            self.output_messages.put(notification_message)
            self.shutdown()
        elif message.type == BgpMessage.UPDATE_MESSAGE:
            notification_message = BgpNotificationMessage(
                BgpNotificationMessage.FINITE_STATE_MACHINE_ERROR)
            self.output_messages.put(notification_message)
            self.shutdown()

    def handle_message_established_state(self, message, tick):
        if message.type == BgpMessage.UPDATE_MESSAGE:
            self.process_route_update(message)
        elif message.type == BgpMessage.KEEPALIVE_MESSAGE:
            self.timers["hold"] = tick
        elif message.type == BgpMessage.NOTIFICATION_MESSAGE:
            self.shutdown()
        elif message.type == BgpMessage.OPEN_MESSAGE:
            notification_message = BgpNotificationMessage(BgpNotificationMessage.CEASE)
            self.output_messages.put(notification_message)
            self.shutdown()

    def process_route_update(self, update_message):
        # we handle both v4 and v6 here, in theory
        # this shouldn't happen in the real world though right?
        for prefix in update_message.nlri:
            route = RouteAddition(
                prefix,
                update_message.path_attributes["next_hop"],
                update_message.path_attributes["as_path"],
                update_message.path_attributes["origin"]
            )
            self.route_updates.put(route)
        if "mp_reach_nlri" in update_message.path_attributes:
            for prefix in update_message.path_attributes["mp_reach_nlri"]["nlri"]:
                route = RouteAddition(
                    prefix,
                    update_message.path_attributes["mp_reach_nlri"]["next_hop"]["afi"],
                    update_message.path_attributes["as_path"],
                    update_message.path_attributes["origin"]
                )
                self.route_updates.put(route)
        for withdrawal in update_message.withdrawn_routes:
            route = RouteRemoval(
                withdrawal
            )
            self.route_updates.put(route)
        if "mp_unreach_nlri" in update_message.path_attributes:
            for withdrawal in update_message.path_attributes["mp_unreach_nlri"]["withdrawn_routes"]:
                route = RouteRemoval(
                    withdrawal
                )
                self.route_updates.put(route)
