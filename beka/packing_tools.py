import struct

def bytes_to_short(bytes_):
    """Convert bytes to short"""
    short, = struct.unpack("!H", bytes_)
    return short

def bytes_to_integer(bytes_):
    """Convert bytes to integer"""
    integer, = struct.unpack("!I", bytes_)
    return integer
