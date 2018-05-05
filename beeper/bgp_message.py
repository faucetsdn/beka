import struct
from beeper.ip4 import ip_number_to_string, ip_string_to_number

class BgpMessage(object):
    OPEN_MESSAGE = 1
    NOTIFICATION_MESSAGE = 3
    KEEPALIVE_MESSAGE = 4
    MARKER = b"\xFF" * 16
    HEADER_LENGTH = 19

    @classmethod
    def pack(cls, message):
        packed_message = message.pack()
        length = cls.HEADER_LENGTH + len(packed_message)
        header = struct.pack("!16sHB", 
            cls.MARKER,
            length,
            message.type
            )
        return header + packed_message

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
        self.type = self.OPEN_MESSAGE

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

    def __str__(self):
        return "BgpOpenMessage: Version %s, Peer AS: %s, Hold time: %s, Identifier: %s" % (
            self.version,
            self.peer_as,
            self.hold_time,
            ip_number_to_string(self.identifier)
            )

class BgpNotificationMessage(BgpMessage):
    def __init__(self, error_code, error_subcode, data):
        self.type = self.NOTIFICATION_MESSAGE
        self.error_code = error_code
        self.error_subcode = error_subcode
        self.data = data

    @classmethod
    def parse(cls, serialised_message):
        error_code, error_subcode = struct.unpack("!BB", serialised_message[:2])
        data = serialised_message[2:]
        return cls(error_code, error_subcode, data)

    def pack(self):
        return struct.pack("!BHHIB",
            self.error_code,
            self.error_subcode,
        ) + self.data

    def __str__(self):
        return "BgpNotificationMessage: Error code: %s, Error subcode: %s, Data: %s" % (
            self.error_code,
            self.error_subcode,
            self.data
            )

class BgpKeepaliveMessage(BgpMessage):
    def __init__(self):
        self.type = self.KEEPALIVE_MESSAGE

    @classmethod
    def parse(cls, serialised_message):
        return cls()

    def pack(self):
        return b""

    def __str__(self):
        return "BgpKeepaliveMessage"

PARSERS = {
    BgpMessage.OPEN_MESSAGE: BgpOpenMessage,
    BgpMessage.NOTIFICATION_MESSAGE: BgpNotificationMessage,
    BgpMessage.KEEPALIVE_MESSAGE: BgpKeepaliveMessage,
}

def parse_bgp_message(message_type, serialised_message):
    return PARSERS[message_type].parse(serialised_message)
