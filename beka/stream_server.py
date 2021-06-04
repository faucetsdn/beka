import socket

from eventlet import GreenPool, listen
import eventlet.greenthread as greenthread


class StreamServer:
    def __init__(self, address, handler):
        self.address = address
        self.handler = handler
        self.greenlets = set()
        self.running = False
        self.server = None

    def _family(self):
        if ":" in self.address[0]:
            return socket.AF_INET6
        return socket.AF_INET

    def serve_forever(self):
        self.running = True
        self.server = listen(self.address, self._family())
        pool = GreenPool()

        try:
            while self.running:
                sock, address = self.server.accept()
                pool.spawn(self.call_handler, sock, address)
                self.greenlets
        except OSError:
            pass

    def call_handler(self, sock, address):
        self.greenlets.add(greenthread.getcurrent())
        self.handler(sock, address)
        self.greenlets.remove(greenthread.getcurrent())

    def stop(self):
        self.running = False
        for greenlet in self.greenlets:
            greenlet.kill()
        self.server.shutdown(socket.SHUT_RDWR)
