import unittest
from unittest.mock import patch, call

from eventlet import GreenPool, sleep
from eventlet.queue import Queue

from beka.peering import Peering


class RouteCatcher():  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.route_updates = []

    def handle(self, route_update):
        self.route_updates.append(route_update)


class FakeStateMachine():  # pylint: disable=too-few-public-methods
    """Mocked StateMachine"""

    def __init__(self):
        self.output_messages = Queue()
        self.route_updates = Queue()


class FakeSocket():  # pylint: disable=too-few-public-methods
    """Mocked Socket"""

    def __init__(self):
        pass

    def makefile(self, *args, **kwargs):  # pylint: disable=unused-argument,no-self-use
        return None


class FakeChopper():  # pylint: disable=too-few-public-methods
    """Mocked Chopper"""

    def __init__(self):
        pass


class PeeringTestCase(unittest.TestCase):
    def setUp(self):
        self.route_catcher = RouteCatcher()
        self.state_machine = FakeStateMachine()
        self.peering = Peering(
            state_machine=self.state_machine,
            peer_address="1.2.3.4:179",
            socket=FakeSocket(),
            route_handler=self.route_catcher.handle
        )
        self.peering.chopper = FakeChopper()

    def test_print_route_updates(self):
        fake_route_update = "FAKE ROUTE UPDATE"
        self.state_machine.route_updates.put(fake_route_update)
        pool = GreenPool()
        eventlet = pool.spawn(self.peering.print_route_updates)
        for _ in range(10):
            sleep(0)
            if self.route_catcher.route_updates:
                break
        self.assertEqual(len(self.route_catcher.route_updates), 1)
        self.assertEqual(self.route_catcher.route_updates[0], fake_route_update)
        eventlet.kill()

    def test_run_starts_threads(self):
        with patch("beka.peering.GreenPool") as GreenPool:
            self.peering.run()
        GreenPool().spawn.assert_has_calls([
            call(self.peering.send_messages),
            call(self.peering.print_route_updates),
            call(self.peering.kick_timers),
            call(self.peering.receive_messages),
        ])
        assert GreenPool().waitall.call_count == 1
