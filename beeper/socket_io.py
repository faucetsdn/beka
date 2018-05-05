class SocketIO:
    def __init__(self, clientsocket):
        self.clientsocket = clientsocket
        self.buffer = b""

    def read(self, num_bytes):
        if num_bytes > len(self.buffer):
            num_extra_bytes = num_bytes - len(self.buffer)
            extra_bytes = self.clientsocket.recv(max(num_extra_bytes, 2048))
            if len(extra_bytes) == 0:
                raise EOFError("Socket closed")
            self.buffer += extra_bytes

        output_bytes = self.buffer[:num_bytes]
        self.buffer = self.buffer[num_bytes:]

        return output_bytes


