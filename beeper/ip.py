from .ip4 import IP4Address, IP4Prefix
from .ip6 import IP6Address, IP6Prefix

class IPAddress:
    @staticmethod
    def from_string(string):
        if ":" in string:
            return IP6Address.from_string(string)
        else:
            return IP4Address.from_string(string)

class IPPrefix:
    @staticmethod
    def from_string(string):
        if ":" in string:
            return IP6Prefix.from_string(string)
        else:
            return IP4Prefix.from_string(string)
