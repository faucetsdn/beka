import struct

def bytes_to_short(bytes_):
    short, = struct.unpack("!H", bytes_)
    return short

def bytes_to_integer(bytes_):
    integer, = struct.unpack("!I", bytes_)
    return integer
