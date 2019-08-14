from beka.ip import IPAddress, IPPrefix
from beka.ip import IP4Address, IP4Prefix
from beka.ip import IP6Address, IP6Prefix
import unittest

class IPAddressTestCase(unittest.TestCase):
    """Test IPAddress and its subclasses"""

    def make_addresses(self, address_strings):
        addresses = []

        for address_string in address_strings:
            addresses.append(IPAddress.from_string(address_string))

        return addresses

    def test_from_string(self):
        ipv4_address_strings = [
            "10.1.1.1",
            "10.1.0.0",
            "192.168.0.23"
        ]

        ipv6_address_strings = [
            "2404:138::1",
            "2404:138::",
            "2404:138::234:1",
            "::1"
        ]

        ipv4_addresses = self.make_addresses(ipv4_address_strings)
        ipv6_addresses = self.make_addresses(ipv6_address_strings)

        for address in ipv4_addresses:
            self.assertTrue(isinstance(address, IP4Address))
        for address in ipv6_addresses:
            self.assertTrue(isinstance(address, IP6Address))
        for address, address_string in zip(ipv4_addresses, ipv4_address_strings):
            self.assertEqual(str(address), address_string)
            self.assertEqual(repr(address), "IP4Address.from_string(\"%s\")" % address_string)
        for address, address_string in zip(ipv6_addresses, ipv6_address_strings):
            self.assertEqual(str(address), address_string)
            self.assertEqual(repr(address), "IP6Address.from_string(\"%s\")" % address_string)


class IPPrefixTestCase(unittest.TestCase):
    """Test IPPrefix and its subclasses"""

    def make_prefixes(self, prefix_strings):
        prefixes = []

        for prefix_string in prefix_strings:
            prefixes.append(IPPrefix.from_string(prefix_string))

        return prefixes

    def test_from_string(self):
        ipv4_prefix_strings = [
            "10.1.1.1/32",
            "10.1.0.0/16",
            "192.168.0.128/20"
        ]

        ipv6_prefix_strings = [
            "2404:138::1/128",
            "2404:138::/32",
            "2404:138::234:1/128",
            "::1/128"
        ]

        ipv4_prefixes = self.make_prefixes(ipv4_prefix_strings)
        ipv6_prefixes = self.make_prefixes(ipv6_prefix_strings)

        for prefix in ipv4_prefixes:
            self.assertTrue(isinstance(prefix, IP4Prefix))
        for prefix in ipv6_prefixes:
            self.assertTrue(isinstance(prefix, IP6Prefix))
        for prefix, prefix_string in zip(ipv4_prefixes, ipv4_prefix_strings):
            self.assertEqual(str(prefix), prefix_string)
            self.assertEqual(repr(prefix), "IP4Prefix.from_string(\"%s\")" % prefix_string)
        for prefix, prefix_string in zip(ipv6_prefixes, ipv6_prefix_strings):
            self.assertEqual(str(prefix), prefix_string)
            self.assertEqual(repr(prefix), "IP6Prefix.from_string(\"%s\")" % prefix_string)
