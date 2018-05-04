from beeper.event import Event

class EventMessageReceived(Event):
    def __init__(self, message):
        # will work but please do this properly
        self.type = self.MESSAGE_RECEIVED
        self.message = message