import struct
import unittest
from io import BytesIO

from beka import chopper

class ChopperTestCase(unittest.TestCase):
    def test_valid_bgp_open_message(self):
        # test bgp open = "\x04\xfe\x09\x00\xb4\xc0\xa8\x00\x0f\x00"
        serialised_data = struct.pack(
            "!16sHB10s20s",
            b"\xFF" * 16,
            29,
            1,
            b"ten bytes!",
            b"junk data at the end"
        )
        expected_message = (1, b"ten bytes!")
        input_stream = BytesIO(serialised_data)
        message = chopper.Chopper(input_stream).next()

        self.assertEqual(message, expected_message)

    def test_bgp_message_invalid_marker(self):
        serialised_data = struct.pack(
            "!16sHB10s20s",
            b"\xFE" * 16,
            29,
            1,
            b"ten bytes!",
            b"junk data at the end"
        )
        input_stream = BytesIO(serialised_data)

        with self.assertRaises(ValueError) as context:
            chopper.Chopper(input_stream).next()

        self.assertEqual("BGP marker missing", str(context.exception))

    def test_bgp_message_invalid_length(self):
        serialised_data = struct.pack(
            "!16sHB10s20s",
            b"\xFF" * 16,
            17,
            1,
            b"ten bytes!",
            b"junk data at the end"
        )
        input_stream = BytesIO(serialised_data)

        with self.assertRaises(ValueError) as context:
            chopper.Chopper(input_stream).next()

        self.assertEqual("Invalid BGP length field", str(context.exception))
