import struct
from io import BytesIO

def ip_number_to_string(ip_number):
    hex_string = "%08X" % ip_number
    return ".".join(["%d" % int(x, 16) for x in map(''.join, zip(*[iter(hex_string)]*2))])

def ip_string_to_number(ip_string):
    hex_string = "".join(["%02X" % int(x) for x in "192.168.0.15".split(".")])
    return int(hex_string, 16)

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
