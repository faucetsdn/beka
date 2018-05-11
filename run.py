import sys
import yaml
import signal

from gevent import spawn, joinall

from beeper.beeper import Beeper

def printmsg(msg):
    sys.stderr.write("%s\n" % msg)
    sys.stderr.flush()

class Server(object):
    def __init__(self):
        self.peering_hosts = []
        self.greenlets = []
        self.beepers = []

    def run(self):
        signal.signal(signal.SIGINT, self.signal_handler)

        with open("beeper.yaml") as file:
            config = yaml.load(file.read())
        peers_per_address = {}
        for peer in config["peers"]:
            if peer["local_address"] not in peers_per_address:
                peers_per_address[peer["local_address"]] = []
            peers_per_address[peer["local_address"]].append(peer)

        for address, peers in peers_per_address.items():
            printmsg("Starting Beeper on %s" % address)
            beeper = Beeper(
                address,
                None,
                peers,
                self.peer_up_handler,
                self.peer_down_handler,
                self.route_handler,
                self.error_handler
            )
            self.beepers.append(beeper)
            self.greenlets.append(spawn(beeper.run))
        joinall(self.greenlets)
        printmsg("All greenlets gone, exiting")

    def signal_handler(self, _signal, _frame):
        printmsg("[SIGINT] Shutting down")
        spawn(self.shutdown)

    def shutdown(self):
        for beeper in self.beepers:
            printmsg("Shutting down Beeper %s" % beeper)
            beeper.shutdown()

    def peer_up_handler(self, peer_ip, peer_as):
        printmsg("[Peer up] %s %d" % (peer_ip, peer_as))

    def peer_down_handler(self, peer_ip, peer_as):
        printmsg("[Peer down] %s %s" % (peer_ip, peer_as))

    def error_handler(self, msg):
        printmsg("[Error] %s" % msg)

    def route_handler(self, route_update):
        if route_update.is_withdraw:
            printmsg("[Route handler] Route removed: %s" % route_update)
        else:
            printmsg("[Route handler] New route received: %s" % route_update)

if __name__ == "__main__":
    server = Server()
    server.run()
