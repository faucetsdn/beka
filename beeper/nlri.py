from io import BytesIO

class IP4Prefix:
    def __init__(self, prefix, length):
        # prefixes are padded to the full length
        # so 10.1.1.0/24 should come in as \x0a\x01\x01\x00, not \x0a\x01\x01
        self.prefix = prefix
        self.length = length

    def __str__(self):
        prefix_string = ".".join(["%d" % x for x in self.prefix])
        return "%s/%d" % (prefix_string, self.length)

    def __eq__(self, other):
        return self.prefix == other.prefix and self.length == other.length

IP4_LENGTH = 4

def unpack_prefix(prefix):
    num_extra_bytes = IP4_LENGTH - len(prefix)

    if num_extra_bytes == 0:
        return prefix
    else:
        return prefix + b"\x00" * num_extra_bytes

def prefix_byte_length(bit_length):
    byte_length = bit_length // 8
    if bit_length % 8:
        byte_length += 1

    return byte_length

def pack_prefix(prefix, length):
    return prefix[:prefix_byte_length(length)]

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

