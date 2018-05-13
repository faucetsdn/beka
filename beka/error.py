class SocketClosedError(Exception):
    def __init__(self, msg):
        super(SocketClosedError, self).__init__(msg)