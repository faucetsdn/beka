from beeper.event import Event
from beeper.message import Message

class Beeper:
    DEFAULT_HOLD_TIME = 60
    DEFAULT_KEEPALIVE_TIME = DEFAULT_HOLD_TIME // 3

    def __init__(self):
        self.timers = {
            "hold": None,
            "keepalive": None,
        }
        self.state = "active"

    def event(self, event):
        if event.type == Event.TIMER_EXPIRED:
            return self.handle_timers(event.epoch)
        elif event.type == Event.MESSAGE_RECEIVED:
            return self.handle_message(event.message)

    def handle_timers(self, epoch):
        output_messages = []

        if self.timers["hold"] < epoch:
            output_messages += self.handle_hold_timer(epoch)

        if self.timers["keepalive"] < epoch:
            output_messages += self.handle_keepalive_timer(epoch)

        return output_messages

    def handle_hold_timer(self, epoch):
        # do stuff
        # should be state check too
        self.state = "active"

        return []

    def handle_keepalive_timer(self, epoch):
        # do stuff
        self.timers["keepalive"] = epoch + self.DEFAULT_KEEPALIVE_TIME

        return []

    def handle_message(self, message):
        output_messages = []

        # state machine
        if self.state == "active":
            if message.type == "open":
                # process open message
                # send open
                # send keepalive
                output_messages.append(Message("open"))
                self.state = "open_confirm"
        elif self.state == "open_confirm":
            if message.type == "keepalive":
                self.state = "established"

        return output_messages

