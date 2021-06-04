import struct
from .error import SocketClosedError
from .bgp_message import BgpMessage

class Chopper(object):
    def __init__(self, input_stream):
        self.input_stream = input_stream

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        header, length, message_type = self.load_header()
        extra_data_length = length - BgpMessage.HEADER_LENGTH
        if extra_data_length > 0:
            serialised_body = self.input_stream.read(extra_data_length)
            if len(serialised_body) < extra_data_length:
                raise SocketClosedError(
                    "Tried to read %d bytes but only got %d" % (extra_data_length, len(header))
                )
        elif extra_data_length < 0:
            raise ValueError("Invalid BGP length field")
        else:
            serialised_body = b""

        return message_type, serialised_body

    def load_header(self):
        # TODO handle when stream runs out
        header = self.input_stream.read(19)
        if len(header) < 19:
            raise SocketClosedError("Tried to read %d bytes but only got %d" % (19, len(header)))

        marker, length, message_type = struct.unpack("!16sHB", header)

        if marker == BgpMessage.MARKER:
            return header, length, message_type

        raise ValueError("BGP marker missing")
