import struct
import socket
from .packing_tools import bytes_to_short, bytes_to_integer
from .ip import IP4Prefix, IP4Address
from .ip import IP6Prefix, IP6Address
from io import BytesIO

class BgpMessage(object):
    OPEN_MESSAGE = 1
    UPDATE_MESSAGE = 2
    NOTIFICATION_MESSAGE = 3
    KEEPALIVE_MESSAGE = 4
    MARKER = b"\xFF" * 16
    HEADER_LENGTH = 19

PARSERS = {}

class BgpMessageParser(object):
    def __init__(self):
        self.capabilities = {}

    def parse(self, message_type, serialised_message):
        return PARSERS[message_type](serialised_message, self.capabilities)

def register_parser(cls):
    PARSERS[cls.MSG_TYPE] = cls.parse
    return cls

class BgpMessagePacker(object):
    def __init__(self):
        self.capabilities = {}

    def pack(self, message):
        packed_message = message.pack(self.capabilities)
        length = BgpMessage.HEADER_LENGTH + len(packed_message)
        header = struct.pack(
            "!16sHB",
            BgpMessage.MARKER,
            length,
            message.MSG_TYPE
            )
        return header + packed_message

MULTIPROTOCOL_TYPES = {
    (1, 1): "ipv4-unicast",
    (2, 1): "ipv6-unicast"
}

def parse_multiprotocol(serialised_capability):
    afi, reserved, safi = struct.unpack("!HBB", serialised_capability)
    if (afi, safi) in MULTIPROTOCOL_TYPES:
        return MULTIPROTOCOL_TYPES[(afi, safi)]
    return (afi, safi)

def parse_routerefresh(serialised_capability):
    return True

def parse_fourbyteas(serialised_capability):
    peer_as, = struct.unpack("!I", serialised_capability)
    return peer_as

capability_parsers = {
    1: parse_multiprotocol,
    2: parse_routerefresh,
    65: parse_fourbyteas
}

capability_keys = {
    1: "multiprotocol",
    2: "routerefresh",
    65: "fourbyteas",
}

def parse_capabilities(serialised_capabilities):
    stream = BytesIO(serialised_capabilities)
    capabilities = {}

    while True:
        serialised_header = stream.read(2)
        if len(serialised_header) == 0:
            break
        capability_code, capability_length = struct.unpack("!BB", serialised_header)
        if capability_code in capability_keys:
            capability_key = capability_keys[capability_code]
            serialised_capability = stream.read(capability_length)
            if capability_key not in capabilities:
                capabilities[capability_key] = []
            capabilities[capability_key].append(capability_parsers[capability_code](serialised_capability))
        else:
            print("WARNING did not recognise capability code %d" % capability_code)

    return capabilities

MULTIPROTOCOL_AFI_SAFI = {
    "ipv4-unicast": (1, 1),
    "ipv6-unicast": (2, 1),
}

def pack_multiprotocol(multiprotocol):
    afi, safi = MULTIPROTOCOL_AFI_SAFI[multiprotocol]
    return struct.pack("!HBB", afi, 0, safi)

def pack_routerefresh(route_refresh):
    return b""

def pack_fourbyteas(fourbyteas):
    return struct.pack("!I", fourbyteas)

capability_packers = {
    "multiprotocol": pack_multiprotocol,
    "routerefresh": pack_routerefresh,
    "fourbyteas": pack_fourbyteas,
}

capability_numbers = {
    "multiprotocol": 1,
    "routerefresh": 2,
    "fourbyteas": 65,
}

OPTIONAL_PARAMETER_CAPABILITY = 2

def pack_capabilities(capabilities):
    packed_capability_list = []

    for capability_key, capability_list in capabilities.items():
        capability_code = capability_numbers[capability_key]
        for capability in capability_list:
            packed_body = capability_packers[capability_key](capability)
            packed_header = struct.pack("!BB", capability_code, len(packed_body))
            packed_capability_list.append(packed_header + packed_body)

    packed_capabilities = b"".join(sorted(packed_capability_list))
    return packed_capabilities

def merge_dict_of_lists(main_dict, new_dict):
    for key, new_list in new_dict.items():
        if key not in main_dict:
            main_dict[key] = new_list
        else:
            main_dict[key] += new_list

def parse_optional_parameters(serialised_optional_parameters):
    stream = BytesIO(serialised_optional_parameters)
    capabilities = {}

    while True:
        serialised_header = stream.read(2)
        if len(serialised_header) == 0:
            break
        parameter_type, parameter_length = struct.unpack("!BB", serialised_header)
        if parameter_type != OPTIONAL_PARAMETER_CAPABILITY:
            raise ValueError("OPEN: Got unsupported optional parameter: %d" % parameter_type)
        serialised_capabilities = stream.read(parameter_length)

        next_capabilities = parse_capabilities(serialised_capabilities)
        merge_dict_of_lists(capabilities, next_capabilities)

    return capabilities

@register_parser
class BgpOpenMessage(BgpMessage):
    MSG_TYPE = BgpMessage.OPEN_MESSAGE

    def __init__(self, version, peer_as, hold_time, identifier, capabilities):
        self.version = version
        self.peer_as = peer_as
        self.hold_time = hold_time
        self.identifier = identifier
        self.capabilities = capabilities

    @classmethod
    def parse(cls, serialised_message, _capabilities):
        version, peer_as, hold_time, identifier, optional_parameters_length = struct.unpack(
            "!BHH4sB",
            serialised_message[:10]
        )
        capabilities = parse_optional_parameters(serialised_message[10:10+optional_parameters_length])
        return cls(version, peer_as, hold_time, IP4Address(identifier), capabilities)

    def pack(self, _capabilities):
        packed_capabilities = pack_capabilities(self.capabilities)
        capabilities_header = struct.pack(
            "!BB",
            OPTIONAL_PARAMETER_CAPABILITY,
            len(packed_capabilities))

        return struct.pack(
            "!BHH4sB",
            self.version,
            self.peer_as,
            self.hold_time,
            self.identifier.address,
            len(capabilities_header + packed_capabilities)
        ) + capabilities_header + packed_capabilities

    def __str__(self):
        return "BgpOpenMessage: Version %s, Peer AS: %s, Hold time: %s, Identifier: %s" % (
            self.version,
            self.peer_as,
            self.hold_time,
            self.identifier
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

ORIGIN_CODES = {
    0: "IGP",
    1: "EGP",
    2: "INCOMPLETE"
}

def parse_origin(packed_origin):
    return ORIGIN_CODES[ord(packed_origin)]

AS_SET_CODE = 1
AS_SEQUENCE_CODE = 2
AS_NUMBER_LENGTH = 2
AS4_NUMBER_LENGTH = 4

def parse_as4_path(packed_as_path):
    # this does as_sets wrong, assumes everything is as_sequence
    input_stream = BytesIO(packed_as_path)
    as_numbers = []
    while True:
        packed_type_and_count = input_stream.read(2)
        if len(packed_type_and_count) == 0:
            break
        type_code, count = struct.unpack("!BB", packed_type_and_count)
        if type_code == AS_SET_CODE:
            print("WARNING received update with AS_SET, treating like AS_SEQUENCE")
        packed_as_sequence = input_stream.read(count * AS4_NUMBER_LENGTH)
        as_numbers += struct.unpack("!" + ("I" * count), packed_as_sequence)
    return " ".join(["%d" % x for x in as_numbers])

def parse_as_path(packed_as_path):
    # this does as_sets wrong, assumes everything is as_sequence
    input_stream = BytesIO(packed_as_path)
    as_numbers = []
    while True:
        packed_type_and_count = input_stream.read(2)
        if len(packed_type_and_count) == 0:
            break
        type_code, count = struct.unpack("!BB", packed_type_and_count)
        if type_code == AS_SET_CODE:
            print("WARNING received update with AS_SET, treating like AS_SEQUENCE")
        packed_as_sequence = input_stream.read(count * AS_NUMBER_LENGTH)
        as_numbers += struct.unpack("!" + ("H" * count), packed_as_sequence)
    return " ".join(["%d" % x for x in as_numbers])

def parse_next_hop(packed_next_hop):
    return IP4Address(packed_next_hop)

IP6_AFI = 2
UNICAST_SAFI = 1

IP6_LENGTH = 16

def unpack_prefix6(prefix):
    num_extra_bytes = IP6_LENGTH - len(prefix)

    if num_extra_bytes == 0:
        return prefix

    return prefix + b"\x00" * num_extra_bytes

def parse_nlri6(stream):
    prefixes = []

    while True:
        serialised_length = stream.read(1)
        if len(serialised_length) == 0:
            break
        prefix_length = ord(serialised_length)
        packed_prefix = stream.read(prefix_byte_length(prefix_length))
        prefix = unpack_prefix6(packed_prefix)
        prefixes.append(IP6Prefix(prefix, prefix_length))

    return prefixes

def parse_mp_reach_nlri(packed_mp_reach_nlri):
    attributes = {}
    stream = BytesIO(packed_mp_reach_nlri)
    afi, safi, next_hop_length = struct.unpack("!HBB", stream.read(4))
    if afi != IP6_AFI:
        raise ValueError("MP_REACH_NLRI: Got unsupported AFI: %d" % afi)
    if safi != UNICAST_SAFI:
        raise ValueError("MP_REACH_NLRI: Got unsupported SAFI: %d" % safi)
    if next_hop_length % IP6_LENGTH != 0:
        raise ValueError("MP_REACH_NLRI: Got unsupported next hop length: %d" % next_hop_length)

    attributes["next_hop"] = []
    for _ in range(next_hop_length // 16):
        attributes["next_hop"].append(IP6Address(struct.unpack("!16s", stream.read(IP6_LENGTH))[0]))

    _reserved_snpa = stream.read(1)

    attributes["nlri"] = parse_nlri6(stream)

    return attributes

def parse_mp_unreach_nlri(packed_mp_reach_nlri):
    attributes = {}
    stream = BytesIO(packed_mp_reach_nlri)
    afi, safi = struct.unpack("!HB", stream.read(3))
    if afi != IP6_AFI:
        raise ValueError("MP_UNREACH_NLRI: Got unsupported AFI: %d" % afi)
    if safi != UNICAST_SAFI:
        raise ValueError("MP_UNREACH_NLRI: Got unsupported SAFI: %d" % safi)

    attributes["withdrawn_routes"] = parse_nlri6(stream)

    return attributes

attribute_parsers = {
    1: parse_origin,
    2: parse_as_path,
    3: parse_next_hop,
    14: parse_mp_reach_nlri,
    15: parse_mp_unreach_nlri,
    17: parse_as4_path,
}

attribute_keys = {
    1: "origin",
    2: "as_path",
    3: "next_hop",
    14: "mp_reach_nlri",
    15: "mp_unreach_nlri",
    17: "as4_path",
}

ORIGIN_NUMBERS = {
    "IGP": 0,
    "EGP": 1,
    "INCOMPLETE": 2
}

def pack_origin(origin):
    return struct.pack("!B", ORIGIN_NUMBERS[origin])

def pack_as4_path(as_path):
    if not as_path:
        return b""

    as_numbers = [int(x) for x in as_path.split(" ")]
    count = len(as_numbers)
    header = struct.pack("!BB", AS_SEQUENCE_CODE, count)
    body = struct.pack("!" + ("I" * count), *as_numbers)
    return header + body

def pack_as_path(as_path):
    if not as_path:
        return b""

    as_numbers = [int(x) for x in as_path.split(" ")]
    count = len(as_numbers)
    header = struct.pack("!BB", AS_SEQUENCE_CODE, count)
    body = struct.pack("!" + ("H" * count), *as_numbers)
    return header + body

def pack_next_hop(next_hop):
    return next_hop.address

def pack_nlri6(nlri):
    packed_nlri = []

    for prefix in nlri:
        packed_prefix = struct.pack("!B", prefix.length) + pack_prefix(prefix.prefix, prefix.length)
        packed_nlri.append(packed_prefix)

    return b"".join(packed_nlri)

def pack_mp_reach_nlri(mp_reach_nlri):
    packed_header = struct.pack(
        "!HBB",
        IP6_AFI,
        UNICAST_SAFI,
        IP6_LENGTH * len(mp_reach_nlri["next_hop"])
    )
    packed_next_hop_list = []
    for next_hop in mp_reach_nlri["next_hop"]:
        packed_next_hop_list.append(struct.pack("!16s", next_hop.address))
    packed_next_hops = b"".join(packed_next_hop_list)
    packed_reserved = struct.pack("!B", 0)
    packed_nlri = pack_nlri6(mp_reach_nlri["nlri"])

    return packed_header + packed_next_hops + packed_reserved + packed_nlri

def pack_mp_unreach_nlri(mp_unreach_nlri):
    packed_header = struct.pack(
        "!HB",
        IP6_AFI,
        UNICAST_SAFI
    )
    packed_withdrawn_route_list = []
    for withdrawn_route in mp_unreach_nlri["withdrawn_routes"]:
        packed_prefix = struct.pack("!B", withdrawn_route.length) + \
            pack_prefix(withdrawn_route.prefix, withdrawn_route.length)
        packed_withdrawn_route_list.append(packed_prefix)
    packed_withdrawn_routes = b"".join(packed_withdrawn_route_list)

    return packed_header + packed_withdrawn_routes

attribute_packers = {
    "origin": pack_origin,
    "as_path": pack_as_path,
    "next_hop": pack_next_hop,
    "mp_reach_nlri" : pack_mp_reach_nlri,
    "mp_unreach_nlri" : pack_mp_unreach_nlri,
    "as4_path": pack_as4_path,
}

attribute_numbers = {
    "origin" : 1,
    "as_path" : 2,
    "next_hop" : 3,
    "mp_reach_nlri" : 14,
    "mp_unreach_nlri" : 15,
    "as4_path" : 17,
}

attribute_flags = {
    "origin" : 0x40,
    "as_path" : 0x40,
    "next_hop" : 0x40,
    "mp_reach_nlri" : 0x80,
    "mp_unreach_nlri" : 0x80,
    "as4_path" : 0xc0,
}

def parse_path_attributes(serialised_path_attributes, fourbyteas):
    stream = BytesIO(serialised_path_attributes)
    path_attributes = {}

    while True:
        attribute_header = stream.read(2)

        if len(attribute_header) == 0:
            break
        flags, type_code = struct.unpack("!BB", attribute_header)

        # TODO factor this pattern out
        if flags & 0x10:
            packed_length = stream.read(2)
            if len(packed_length) == 0:
                break
            length, = struct.unpack("!H", packed_length)
        else:
            packed_length = stream.read(1)
            if len(packed_length) == 0:
                break
            length, = struct.unpack("!B", packed_length)

        packed_attribute = stream.read(length)

        if type_code in attribute_parsers:
            # TODO we're ignoring the flags here, these should at very least be preserved
            # this is tightly coupled, there's gotta be a better way to do this
            if fourbyteas and attribute_keys[type_code] == "as_path":
                path_attributes["as_path"] = parse_as4_path(packed_attribute)
            else:
                path_attributes[attribute_keys[type_code]] = attribute_parsers[type_code](packed_attribute)
        else:
            print("WARNING did not recognise BGP path attribute type %d" % type_code)

    return path_attributes

def parse_withdrawn_routes(serialised_withdrawn_routes):
    stream = BytesIO(serialised_withdrawn_routes)
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

PATH_ATTRIBUTE_ORDER = {
    "origin" : 1,
    "as_path" : 2,
    "as4_path" : 3,
    "next_hop" : 4,
    "mp_reach_nlri" : 5,
    "mp_unreach_nlri" : 6,
}

@register_parser
class BgpUpdateMessage(BgpMessage):
    MSG_TYPE = BgpMessage.UPDATE_MESSAGE

    def __init__(self, withdrawn_routes, path_attributes, nlri):
        self.withdrawn_routes = withdrawn_routes
        self.path_attributes = path_attributes
        self.nlri = nlri

    @classmethod
    def parse(cls, serialised_message, capabilities):
        data_stream = BytesIO(serialised_message)
        withdrawn_routes_length = bytes_to_short(data_stream.read(2))
        serialised_withdrawn_routes = data_stream.read(withdrawn_routes_length)
        withdrawn_routes = parse_withdrawn_routes(serialised_withdrawn_routes)

        total_path_attribute_length = bytes_to_short(data_stream.read(2))
        serialised_path_attributes = data_stream.read(total_path_attribute_length)
        path_attributes = parse_path_attributes(serialised_path_attributes, "fourbyteas" in capabilities)

        serialised_nlri = data_stream.read()
        nlri = parse_nlri(serialised_nlri)

        return cls(withdrawn_routes, path_attributes, nlri)

    def pack(self, capabilities):
        # TODO pack withdrawn routes
        packed_withdrawn_routes = self.pack_withdrawn_routes()
        packed_withdrawn_routes_length = struct.pack("!H", len(packed_withdrawn_routes))
        packed_path_attributes = self.pack_path_attributes("fourbyteas" in capabilities)
        packed_path_attributes_length = struct.pack("!H", len(packed_path_attributes))
        packed_nlri = self.pack_nlri()
        return packed_withdrawn_routes_length + \
            packed_withdrawn_routes + \
            packed_path_attributes_length + \
            packed_path_attributes + \
            packed_nlri

    def pack_withdrawn_routes(self):
        packed_routes_list = []

        for prefix in self.withdrawn_routes:
            packed_route = struct.pack("!B", prefix.length) + pack_prefix(prefix.prefix, prefix.length)
            packed_routes_list.append(packed_route)

        return b"".join(packed_routes_list)

    def pack_path_attributes(self, fourbyteas):
        packed_path_attributes = []
        sorted_attribute_pairs = sorted(self.path_attributes.items(), key=lambda x: PATH_ATTRIBUTE_ORDER[x[0]])
        for name, path_attribute in sorted_attribute_pairs:
            if fourbyteas and name=="as_path":
                packed_entry = pack_as4_path(path_attribute)
            else:
                packed_entry = attribute_packers[name](path_attribute)
            packed_header = struct.pack(
                "!BBB",
                attribute_flags[name],
                attribute_numbers[name],
                len(packed_entry)
            )
            packed_path_attribute = packed_header + packed_entry
            packed_path_attributes.append(packed_path_attribute)

        return b"".join(packed_path_attributes)

    def pack_nlri(self):
        packed_nlri = []

        for prefix in self.nlri:
            # TODO this feels like it should be on IP4Prefix
            packed_prefix = struct.pack("!B", prefix.length) + pack_prefix(prefix.prefix, prefix.length)
            packed_nlri.append(packed_prefix)

        return b"".join(packed_nlri)

    def __str__(self):
        return "BgpUpdateMessage: Withdrawn routes: %s, Path attributes: %s, NLRI: %s" % (
            [str(x) for x in self.withdrawn_routes],
            self.path_attributes,
            [str(x) for x in self.nlri]
            )

@register_parser
class BgpNotificationMessage(BgpMessage):
    MSG_TYPE = BgpMessage.NOTIFICATION_MESSAGE

    MESSAGE_HEADER_ERROR = 1
    OPEN_MESSAGE_ERROR = 2
    UPDATE_MESSAGE_ERROR = 3
    HOLD_TIMER_EXPIRED = 4
    FINITE_STATE_MACHINE_ERROR = 5
    CEASE = 6

    def __init__(self, error_code, error_subcode=0, data=b""):
        self.error_code = error_code
        self.error_subcode = error_subcode
        self.data = data

    @classmethod
    def parse(cls, serialised_message, _capabilities):
        error_code, error_subcode = struct.unpack("!BB", serialised_message[:2])
        data = serialised_message[2:]
        return cls(error_code, error_subcode, data)

    def pack(self, _capabilities):
        return struct.pack(
            "!BB",
            self.error_code,
            self.error_subcode,
        ) + self.data

    def __str__(self):
        return "BgpNotificationMessage: Error code: %s, Error subcode: %s, Data: %s" % (
            self.error_code,
            self.error_subcode,
            self.data
            )

@register_parser
class BgpKeepaliveMessage(BgpMessage):
    MSG_TYPE = BgpMessage.KEEPALIVE_MESSAGE

    def __init__(self):
        pass

    @classmethod
    def parse(cls, serialised_message, _capabilities):
        return cls()

    def pack(self, _capabilities):
        return b""

    def __eq__(self, other):
        return type(other) == type(self)

    def __str__(self):
        return "BgpKeepaliveMessage"
