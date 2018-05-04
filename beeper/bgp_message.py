import struct

class BgpMessage(object):
    OPEN_MESSAGE = 2
    KEEPALIVE_MESSAGE = 3

    def __init__(self):
        pass

def _register_parser(msg_type):
    def _register_cls_parser(cls):
        cls.cls_msg_type = msg_type
        return cls
    return _set_cls_msg_type

def _register_parser(cls):
    BgpMessage.PARSERS[cls.cls_msg_type] = cls.parser
    return cls

class BgpOpenMessage(BgpMessage):
    def __init__(self, version, peer_as, hold_time, identifier):
        self.version = version
        self.peer_as = peer_as
        self.hold_time = hold_time
        self.identifier = identifier

    @classmethod
    def parse(cls, serialised_message):
        # we ignore optional parameters
        version, peer_as, hold_time, identifier, optional_parameters_length = struct.unpack("!BHHIB", serialised_message[:10])
        return cls(version, peer_as, hold_time, identifier)

    def pack(self):
        return struct.pack("!BHHIB",
            self.version,
            self.peer_as,
            self.hold_time,
            self.identifier,
            0
        )

class BgpKeepaliveMessage(BgpMessage):
    def __init__(self):
        pass

    @classmethod
    def parse(cls, serialised_message):
        return cls()

    def pack(self):
        return b""

PARSERS = {
    BgpMessage.OPEN_MESSAGE: BgpOpenMessage,
    BgpMessage.KEEPALIVE_MESSAGE: BgpKeepaliveMessage,
}

def parse_bgp_message(message_type, serialised_message):
    return PARSERS[message_type].parse(serialised_message)
