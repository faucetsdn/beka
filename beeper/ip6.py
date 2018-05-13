import struct
import socket
from io import BytesIO

class IP6Address:
    def __init__(self, address):
        self.address = address

    @classmethod
    def from_string(cls, address_string):
        address = socket.inet_pton(socket.AF_INET6, address_string)

        return cls(address)

    def __str__(self):
        address_string = socket.inet_ntop(socket.AF_INET6, self.address)
        return address_string

    def __repr__(self):
        return "IP6Address.from_string(\"%s\")" % self.__str__()

    def __eq__(self, other):
        return self.address == other.address

    def __hash__(self):
        return hash(self.address)

class IP6Prefix:
    def __init__(self, prefix, length):
        self.prefix = prefix
        self.length = length

    @classmethod
    def from_string(cls, string):
        prefix_string, length_string = string.split("/")
        prefix = socket.inet_pton(socket.AF_INET6, prefix_string)

        return cls(prefix, int(length_string, 10))

    def __str__(self):
        prefix_string = socket.inet_ntop(socket.AF_INET6, self.prefix)
        return "%s/%d" % (prefix_string, self.length)

    def __repr__(self):
        return "IP6Prefix.from_string(\"%s\")" % self.__str__()

    def __eq__(self, other):
        return self.prefix == other.prefix and self.length == other.length
