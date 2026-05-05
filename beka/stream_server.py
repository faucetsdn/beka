import socket
import threading
from concurrent.futures import ThreadPoolExecutor


class StreamServer:
    """Listen on ``address`` and dispatch each accepted socket to ``handler`` in its own thread."""

    DEFAULT_MAX_HANDLERS = 64

    def __init__(self, address, handler):
        self.address = address
        self.handler = handler
        self.running = False
        self.server = None
        self._executor = None
        self._accept_thread = None

    def _family(self):
        if ":" in self.address[0]:
            return socket.AF_INET6
        return socket.AF_INET

    def serve_forever(self):
        self.running = True
        self.server = socket.socket(self._family(), socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(self.address)
        self.server.listen()
        self._executor = ThreadPoolExecutor(
            max_workers=self.DEFAULT_MAX_HANDLERS,
            thread_name_prefix="beka-handler",
        )
        self._accept_thread = threading.current_thread()
        try:
            while self.running:
                try:
                    sock, address = self.server.accept()
                except OSError:
                    # accept() raises after stop() shuts the listening socket
                    break
                self._executor.submit(self.handler, sock, address)
        finally:
            self._executor.shutdown(wait=False)
            self._executor = None

    def stop(self):
        self.running = False
        if self.server is not None:
            try:
                self.server.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.server.close()
            except OSError:
                pass
