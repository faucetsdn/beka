class Event(object):
    TIMER_EXPIRED = 1
    MESSAGE_RECEIVED = 2

class EventTimerExpired(Event):
    def __init__(self, epoch):
        # will work but please do this properly
        self.type = self.TIMER_EXPIRED
        self.epoch = epoch

class EventMessageReceived(Event):
    def __init__(self, message):
        # will work but please do this properly
        self.type = self.MESSAGE_RECEIVED
        self.message = message