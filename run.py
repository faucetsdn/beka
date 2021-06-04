import signal
import sys
import yaml

from eventlet import GreenPool

from beka.beka import Beka


def printmsg(msg):
    sys.stderr.write("%s\n" % msg)
    sys.stderr.flush()


class Server():
    def __init__(self):
        self.peering_hosts = []
        self.greenlets = []
        self.bekas = []

    def run(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        pool = GreenPool()

        with open("beka.yaml") as file:
            config = yaml.load(file.read())
        for router in config["routers"]:
            printmsg("Starting Beka on %s" % router["local_address"])
            beka = Beka(
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
                beka.add_neighbor(
                    "passive",
                    peer["peer_ip"],
                    peer["peer_as"],
                )
            if "routes" in router:
                for route in router["routes"]:
                    beka.add_route(
                        route["prefix"],
                        route["next_hop"]
                    )
            self.bekas.append(beka)
            pool.spawn_n(beka.run)
        pool.waitall()
        printmsg("All greenlets gone, exiting")

    def signal_handler(self, _signal, _frame):
        printmsg("[SIGINT] Shutting down")
        self.shutdown()

    def shutdown(self):
        for beka in self.bekas:
            printmsg("Shutting down Beka %s" % beka)
            beka.shutdown()

    def peer_up_handler(self, peer_ip, peer_as):  # pylint: disable=no-self-use
        printmsg("[Peer up] %s %d" % (peer_ip, peer_as))

    def peer_down_handler(self, peer_ip, peer_as):  # pylint: disable=no-self-use
        printmsg("[Peer down] %s %s" % (peer_ip, peer_as))

    def error_handler(self, msg):  # pylint: disable=no-self-use
        printmsg("[Error] %s" % msg)

    def route_handler(self, route_update):  # pylint: disable=no-self-use
        if route_update.is_withdraw:
            printmsg("[Route handler] Route removed: %s" % route_update)
        else:
            printmsg("[Route handler] New route received: %s" % route_update)


if __name__ == "__main__":
    server = Server()
    server.run()
