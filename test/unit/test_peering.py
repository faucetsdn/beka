import threading
import time
import unittest
from queue import Queue
from unittest.mock import patch, call

from beka.peering import Peering


class RouteCatcher:  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.route_updates = []

    def handle(self, route_update):
        self.route_updates.append(route_update)


class FakeStateMachine:  # pylint: disable=too-few-public-methods
    """Mocked StateMachine"""

    def __init__(self):
        self.output_messages = Queue()
        self.route_updates = Queue()


class FakeSocket:  # pylint: disable=too-few-public-methods
    """Mocked Socket"""

    def makefile(self, *args, **kwargs):  # pylint: disable=unused-argument
        return None

    def shutdown(self, _how):  # pragma: no cover - exercised via Peering.shutdown
        pass


class FakeChopper:  # pylint: disable=too-few-public-methods
    """Mocked Chopper"""


class PeeringTestCase(unittest.TestCase):
    def setUp(self):
        self.route_catcher = RouteCatcher()
        self.state_machine = FakeStateMachine()
        self.peering = Peering(
            state_machine=self.state_machine,
            peer_address="1.2.3.4:179",
            socket=FakeSocket(),
            route_handler=self.route_catcher.handle,
        )
        self.peering.chopper = FakeChopper()

    def test_print_route_updates(self):
        fake_route_update = "FAKE ROUTE UPDATE"
        self.state_machine.route_updates.put(fake_route_update)
        thread = threading.Thread(target=self.peering.print_route_updates, daemon=True)
        thread.start()
        deadline = time.monotonic() + 1.0
        while not self.route_catcher.route_updates and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(len(self.route_catcher.route_updates), 1)
        self.assertEqual(self.route_catcher.route_updates[0], fake_route_update)
        # Cooperative shutdown unblocks the consumer's Queue.get().
        self.peering.shutdown()
        thread.join(timeout=1)
        self.assertFalse(thread.is_alive())

    def test_run_starts_threads(self):
        with patch("beka.peering.threading.Thread") as Thread:
            self.peering.run()
        Thread.assert_has_calls(
            [
                call(
                    target=self.peering.send_messages, name="send_messages", daemon=True
                ),
                call(
                    target=self.peering.print_route_updates,
                    name="print_route_updates",
                    daemon=True,
                ),
                call(target=self.peering.kick_timers, name="kick_timers", daemon=True),
                call(
                    target=self.peering.receive_messages,
                    name="receive_messages",
                    daemon=True,
                ),
            ],
            any_order=False,
        )
        # Each thread should be started and then joined.
        self.assertEqual(Thread.return_value.start.call_count, 4)
        self.assertEqual(Thread.return_value.join.call_count, 4)
