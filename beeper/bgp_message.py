import struct
from beeper.ip4 import ip_number_to_string, ip_string_to_number
from beeper.packing_tools import bytes_to_short, bytes_to_integer
from beeper.ip4 import IP4Prefix
from io import BytesIO

class BgpMessage(object):
    OPEN_MESSAGE = 1
    UPDATE_MESSAGE = 2
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

IP4_LENGTH = 4

def prefix_byte_length(bit_length):
    byte_length = bit_length // 8
    if bit_length % 8:
        byte_length += 1

    return byte_length

def pack_prefix(prefix, length):
    return prefix[:prefix_byte_length(length)]

def unpack_prefix(prefix):
    num_extra_bytes = IP4_LENGTH - len(prefix)

    if num_extra_bytes == 0:
        return prefix
    else:
        return prefix + b"\x00" * num_extra_bytes

def parse_nlri(serialised_nlri):
    stream = BytesIO(serialised_nlri)
    prefixes = []

    while True:
        serialised_length = stream.read(1)
        if len(serialised_length) == 0:
            break
        prefix_length = ord(serialised_length)
        packed_prefix = stream.read(prefix_byte_length(prefix_length))
        prefix = unpack_prefix(packed_prefix)
        prefixes.append(IP4Prefix(prefix, prefix_length))

    return prefixes

def parse_next_hop(packed_next_hop):
    # TODO make this more meaningful than just a string
    return "NEXT_HOP: %s" % ".".join(["%d" % x for x in packed_next_hop])

attribute_parsers = {
    3 : parse_next_hop
}

def parse_path_attributes(serialised_path_attributes):
    stream = BytesIO(serialised_path_attributes)
    path_attributes = []

    while True:
        attribute_header = stream.read(3)
        if len(attribute_header) == 0:
            break
        flags, type_code, length = struct.unpack("!BBB", attribute_header)
        packed_attribute = stream.read(length)

        if type_code in attribute_parsers:
            # TODO we're ignoring the flags here, these should at very least be preserved
            path_attributes.append(attribute_parsers[type_code](packed_attribute))
        else:
            print("WARNING did not recognise BGP path attribute type %d" % type_code)

    return path_attributes

class BgpUpdateMessage(BgpMessage):
    def __init__(self, withdrawn_routes, path_attributes, nlri):
        self.type = self.UPDATE_MESSAGE
        self.withdrawn_routes = withdrawn_routes
        self.path_attributes = path_attributes
        self.nlri = nlri

    @classmethod
    def parse(cls, serialised_message):
        data_stream = BytesIO(serialised_message)
        # TODO route withdrawals
        withdrawn_routes_length = bytes_to_short(data_stream.read(2))
        serialised_withdrawn_routes = data_stream.read(withdrawn_routes_length)

        # TODO path attributes
        total_path_attribute_length = bytes_to_short(data_stream.read(2))
        serialised_path_attributes = data_stream.read(total_path_attribute_length)
        print("Path attributes length: %d" % total_path_attribute_length)
        path_attributes = parse_path_attributes(serialised_path_attributes)

        serialised_nlri = data_stream.read()
        nlri = parse_nlri(serialised_nlri)
        # TODO nlri

        return cls([], path_attributes, nlri)

    def pack(self):
        return b""

    def __str__(self):
        return "BgpUpdateMessage: Widthdrawn routes: %s, Path attributes: %s, NLRI: %s" % (
            [str(x) for x in self.withdrawn_routes],
            [str(x) for x in self.path_attributes],
            [str(x) for x in self.nlri]
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
    BgpMessage.UPDATE_MESSAGE: BgpUpdateMessage,
    BgpMessage.NOTIFICATION_MESSAGE: BgpNotificationMessage,
    BgpMessage.KEEPALIVE_MESSAGE: BgpKeepaliveMessage,
}

def parse_bgp_message(message_type, serialised_message):
    return PARSERS[message_type].parse(serialised_message)
