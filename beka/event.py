class Event():  # pylint: disable=too-few-public-methods
    TIMER_EXPIRED = 1
    MESSAGE_RECEIVED = 2
    SHUTDOWN = 3


class EventTimerExpired(Event):  # pylint: disable=too-few-public-methods
    """Event used to indicate timer has expired"""

    def __init__(self):
        # will work but please do this properly
        self.type = self.TIMER_EXPIRED


class EventMessageReceived(Event):  # pylint: disable=too-few-public-methods
    """Event used to indicate message has been received"""

    def __init__(self, message):
        # will work but please do this properly
        self.type = self.MESSAGE_RECEIVED
        self.message = message


class EventShutdown(Event):  # pylint: disable=too-few-public-methods
    """Event used to indicate shutdown"""

    def __init__(self):
        # will work but please do this properly
        self.type = self.SHUTDOWN
