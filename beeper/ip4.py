import struct

def ip_number_to_string(ip_number):
    hex_string = "%08X" % ip_number
    return ".".join(["%d" % int(x, 16) for x in map(''.join, zip(*[iter(hex_string)]*2))])

def ip_string_to_number(ip_string):
    hex_string = "".join(["%02X" % int(x) for x in "192.168.0.15".split(".")])
    return int(hex_string, 16)
