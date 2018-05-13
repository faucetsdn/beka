"""IP address and prefix classes"""

import socket

def is_ipv6(address_string):
    """Checks if a string is an IPv6 address or prefix"""

    return ":" in address_string

class IPBase(object): # pylint: disable=too-few-public-methods
    """Abstract base class for IP addresses and prefixes"""

    def __repr__(self):
        return "%s.from_string(\"%s\")" % (self.__class__.__name__, self.__str__())

class IPAddress(IPBase): # pylint: disable=too-few-public-methods
    """Abstract base class for IP addresses"""

    INET_TYPE = None

    def __init__(self, address):
        """Common constructor for IP addresses"""

        self.address = address

    def __str__(self):
        """Common str() for IP addresses"""

        address_string = socket.inet_ntop(self.INET_TYPE, self.address)
        return address_string

    def __eq__(self, other):
        """Common equality checker for IP addresses"""

        return self.address == other.address

    def __hash__(self):
        """Common hash method for IP addresses"""

        return hash(self.address)

    @staticmethod
    def from_string(string):
        """Common from_string method for IP addresses"""

        if is_ipv6(string):
            return IP6Address.build_from_string(string)
        return IP4Address.build_from_string(string)


class IPPrefix(IPBase): # pylint: disable=too-few-public-methods
    """Abstract base class for IP prefixes"""

    INET_TYPE = None

    def __init__(self, prefix, length):
        """Common constructor for IP prefixes"""

        self.prefix = prefix
        self.length = length

    def __str__(self):
        """Common str() for IP prefixes"""

        prefix_string = socket.inet_ntop(self.INET_TYPE, self.prefix)
        return "%s/%d" % (prefix_string, self.length)

    def __eq__(self, other):
        """Common equality checker for IP prefixes"""

        return self.prefix == other.prefix and self.length == other.length

    @staticmethod
    def from_string(string):
        """Common from_string method for IP prefixes"""

        if is_ipv6(string):
            return IP6Prefix.build_from_string(string)
        return IP4Prefix.build_from_string(string)


class IP4Address(IPAddress): # pylint: disable=too-few-public-methods
    """An IPv4 address"""

    INET_TYPE = socket.AF_INET

    @classmethod
    def build_from_string(cls, address_string):
        """Concrete build_from_string method"""

        address = socket.inet_pton(cls.INET_TYPE, address_string)

        return cls(address)

class IP4Prefix(IPPrefix): # pylint: disable=too-few-public-methods
    """An IPv4 prefix"""

    INET_TYPE = socket.AF_INET

    @classmethod
    def build_from_string(cls, string):
        """Concrete build_from_string method"""

        prefix_string, length_string = string.split("/")
        prefix = socket.inet_pton(cls.INET_TYPE, prefix_string)

        return cls(prefix, int(length_string, 10))

class IP6Address(IPAddress): # pylint: disable=too-few-public-methods
    """An IPv6 address"""

    INET_TYPE = socket.AF_INET6

    @classmethod
    def build_from_string(cls, address_string):
        """Concrete build_from_string method"""

        address = socket.inet_pton(socket.AF_INET6, address_string)

        return cls(address)

class IP6Prefix(IPPrefix): # pylint: disable=too-few-public-methods
    """An IPv6 prefix"""

    INET_TYPE = socket.AF_INET6

    @classmethod
    def build_from_string(cls, string):
        """Concrete build_from_string method"""

        prefix_string, length_string = string.split("/")
        prefix = socket.inet_pton(socket.AF_INET6, prefix_string)

        return cls(prefix, int(length_string, 10))
