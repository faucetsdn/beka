import sys
import yaml
import signal

from eventlet import GreenPool

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
        pool = GreenPool()

        with open("beeper.yaml") as file:
            config = yaml.load(file.read())
        for router in config["routers"]:
            printmsg("Starting Beeper on %s" % router["local_address"])
            beeper = Beeper(
                router["local_address"],
                router["bgp_port"],
                router["local_as"],
                router["router_id"],
                self.peer_up_handler,
                self.peer_down_handler,
                self.route_handler,
                self.error_handler
            )
            for peer in router["peers"]:
                beeper.add_neighbor(
                    "passive",
                    peer["peer_ip"],
                    peer["peer_as"],
                )
            if "routes" in router:
                for route in router["routes"]:
                    beeper.add_route(
                        route["prefix"],
                        route["next_hop"]
                    )
            self.beepers.append(beeper)
            pool.spawn_n(beeper.run)
        pool.waitall()
        printmsg("All greenlets gone, exiting")

    def signal_handler(self, _signal, _frame):
        printmsg("[SIGINT] Shutting down")
        self.shutdown()

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
