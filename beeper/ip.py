from beeper.ip4 import IP4Address
from beeper.ip6 import IP6Address

class IPAddress:
    @staticmethod
    def from_string(string):
        if ":" in string:
            return IP6Address.from_string(string)
        else:
            return IP4Address.from_string(string)
