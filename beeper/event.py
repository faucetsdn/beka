class Event(object):
    TIMER_EXPIRED = 1
    MESSAGE_RECEIVED = 2

class MessageEvent(Event):
    def __init__(self, message):
        self.message = message
        self.type = self.MESSAGE_RECEIVED