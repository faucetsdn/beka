from eventlet.queue import Queue
from collections import OrderedDict

from .event import Event
from .bgp_message import BgpMessage, BgpOpenMessage, BgpUpdateMessage
from .bgp_message import BgpKeepaliveMessage, BgpNotificationMessage
from .route import RouteAddition, RouteRemoval
from .ip import IPAddress, IPPrefix
from .ip import IP4Address, IP4Prefix
from .ip import IP6Address, IP6Prefix
from .timer import Timer
from .error import IdleError

class StateMachine:
    DEFAULT_HOLD_TIME = 240
    DEFAULT_KEEPALIVE_TIME = DEFAULT_HOLD_TIME // 3

    def __init__(self, local_as, peer_as, router_id, local_address, neighbor,
                 hold_time=DEFAULT_HOLD_TIME, open_handler=None):
        self.local_as = local_as
        if local_as > 65535:
            self.local_as2 = 23456
        else:
            self.local_as2 = self.local_as
        self.peer_as = peer_as
        self.router_id = IPAddress.from_string(router_id)
        self.local_address = IPAddress.from_string(local_address)
        self.neighbor = IPAddress.from_string(neighbor)
        self.hold_time = hold_time
        self.open_handler = open_handler

        self.keepalive_time = hold_time // 3
        self.output_messages = Queue()
        self.route_updates = Queue()
        self.routes_to_advertise = []
        self.fourbyteas = False

        self.timers = {
            "hold": Timer(self.hold_time),
            "keepalive": Timer(self.keepalive_time),
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
        self.shutdown("Shutdown requested")

    def shutdown(self, message):
        self.state = "idle"
        raise IdleError("State machine stopping: %s" % message)

    def handle_timers(self, tick):
        if self.timers["hold"].expired(tick):
            self.handle_hold_timer()
        if self.timers["keepalive"].expired(tick):
            self.handle_keepalive_timer(tick)

    def handle_hold_timer(self):
        notification_message = BgpNotificationMessage(BgpNotificationMessage.HOLD_TIMER_EXPIRED)
        self.output_messages.put(notification_message)
        self.shutdown("Hold timer expired")

    def handle_keepalive_timer(self, tick):
        self.timers["keepalive"].reset(tick)
        message = BgpKeepaliveMessage()
        self.output_messages.put(message)

    def handle_message(self, message, tick):# state machine
        if self.state == "active":
            self.handle_message_active_state(message, tick)
        elif self.state == "open_sent":
            self.handle_message_open_sent_state(message, tick)
        elif self.state == "open_confirm":
            self.handle_message_open_confirm_state(message, tick)
        elif self.state == "established":
            self.handle_message_established_state(message, tick)

    def handle_message_active_state(self, message, tick):
        if isinstance(message, BgpOpenMessage):
            # TODO sanity check incoming open message
            if "fourbyteas" in message.capabilities:
                self.fourbyteas = message.capabilities["fourbyteas"]

            if self.open_handler:
                self.open_handler(message.capabilities)

            capabilities = {
                "fourbyteas": [self.local_as]
            }
            ipv4_capabilities = {"multiprotocol": ["ipv4-unicast"]}
            ipv6_capabilities = {"multiprotocol": ["ipv6-unicast"]}
            if isinstance(self.local_address, IP4Address):
                capabilities.update(ipv4_capabilities)
            elif isinstance(self.local_address, IP6Address):
                capabilities.update(ipv6_capabilities)
            open_message = BgpOpenMessage(4, self.local_as2, self.hold_time, self.router_id, capabilities)
            keepalive_message = BgpKeepaliveMessage()
            self.output_messages.put(open_message)
            self.output_messages.put(keepalive_message)
            self.timers["hold"].reset(tick)
            self.timers["keepalive"].reset(tick)
            self.state = "open_confirm"
        else:
            self.shutdown("Invalid message in Active state: %s" % str(message))

    def handle_message_open_sent_state(self, message, tick):
        if isinstance(message, BgpOpenMessage):
            # TODO sanity check incoming open message
            if "fourbyteas" in message.capabilities:
                self.fourbyteas = message.capabilities["fourbyteas"]

            if self.open_handler:
                self.open_handler(message.capabilities)

            capabilities = {
                "fourbyteas": [self.local_as]
            }
            ipv4_capabilities = {"multiprotocol": ["ipv4-unicast"]}
            ipv6_capabilities = {"multiprotocol": ["ipv6-unicast"]}
            if isinstance(self.local_address, IP4Address):
                capabilities.update(ipv4_capabilities)
            elif isinstance(self.local_address, IP6Address):
                capabilities.update(ipv6_capabilities)
            keepalive_message = BgpKeepaliveMessage()
            self.output_messages.put(keepalive_message)
            self.timers["hold"].reset(tick)
            self.timers["keepalive"].reset(tick)
            self.state = "open_confirm"
        else:
            self.shutdown("Invalid message in OpenSent state: %s" % str(message))

    def handle_message_open_confirm_state(self, message, tick):
        if isinstance(message, BgpKeepaliveMessage):
            for message in self.build_update_messages():
                self.output_messages.put(message)
            self.timers["hold"].reset(tick)
            self.timers["keepalive"].reset(tick)
            self.state = "established"
        elif isinstance(message, BgpNotificationMessage):
            self.shutdown("Notification message received %s" % str(message))
        elif isinstance(message, BgpOpenMessage):
            notification_message = BgpNotificationMessage(BgpNotificationMessage.CEASE)
            self.output_messages.put(notification_message)
            self.shutdown("Received Open message in OpenConfirm state")
        elif isinstance(message, BgpUpdateMessage):
            notification_message = BgpNotificationMessage(
                BgpNotificationMessage.FINITE_STATE_MACHINE_ERROR)
            self.output_messages.put(notification_message)
            self.shutdown("Received Update message in OpenConfirm state")

    def handle_message_established_state(self, message, tick):
        if isinstance(message, BgpUpdateMessage):
            self.process_route_update(message)
        elif isinstance(message, BgpKeepaliveMessage):
            self.timers["hold"].reset(tick)
        elif isinstance(message, BgpNotificationMessage):
            self.shutdown("Notification message received %s" % str(message))
        elif isinstance(message, BgpOpenMessage):
            notification_message = BgpNotificationMessage(BgpNotificationMessage.CEASE)
            self.output_messages.put(notification_message)
            self.shutdown("Received Open message in Established state")

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
                    update_message.path_attributes["mp_reach_nlri"]["next_hop"][0],
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

    def build_update_messages(self):
        # TODO handle withdrawals
        route_additions = list(filter(lambda x: isinstance(x, RouteAddition), self.routes_to_advertise))
        ipv4_route_additions = filter(lambda x: isinstance(x.prefix, IP4Prefix), route_additions)
        ipv6_route_additions = filter(lambda x: isinstance(x.prefix, IP6Prefix), route_additions)

        return self.build_ipv4_update_messages(ipv4_route_additions) + \
            self.build_ipv6_update_messages(ipv6_route_additions)

    def build_ipv4_update_messages(self, ipv4_route_additions):
        update_messages = []
        nlri_by_path = OrderedDict()
        for route_addition in ipv4_route_additions:
            path_key = (
                ("next_hop", route_addition.next_hop),
                ("as_path", route_addition.as_path),
                ("origin", route_addition.origin)
            )
            nlri_by_path.setdefault(path_key, []).append(route_addition.prefix)

        for path_attributes, nlri in nlri_by_path.items():
            update_messages.append(BgpUpdateMessage([], dict(path_attributes), nlri))

        return update_messages

    def build_ipv6_update_messages(self, ipv6_route_additions):
        update_messages = []
        nlri_by_path = OrderedDict()
        for route_addition in ipv6_route_additions:
            path_key = (
                ("next_hop", route_addition.next_hop),
                ("as_path", route_addition.as_path),
                ("origin", route_addition.origin)
            )
            nlri_by_path.setdefault(path_key, []).append(route_addition.prefix)

        for path_attributes, nlri in nlri_by_path.items():
            path_attributes_dict = dict(path_attributes)
            path_attributes_v6 = {
                "as_path": path_attributes_dict["as_path"],
                "origin": path_attributes_dict["origin"],
                "mp_reach_nlri": {
                    "next_hop": [
                        path_attributes_dict["next_hop"],
                    ],
                    "nlri": nlri
                }
            }
            update_messages.append(BgpUpdateMessage([], path_attributes_v6, []))

        return update_messages
