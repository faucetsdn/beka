import socket
import sys
from beeper.beeper import Beeper
from beeper.chopper import Chopper

BGP_PORT = 179
ADDRESS = '0.0.0.0'

def printmsg(msg):
    sys.stderr.write("%s\n" % msg)
    sys.stderr.flush()

def server(socket, beeper):
    chopper = Chopper()


def run():
    printmsg("Creating beeper")
    beeper = Beeper()

    printmsg("Creating socket")
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind((ADDRESS, BGP_PORT))
    serversocket.listen(5)

    while True:
        (clientsocket, address) = serversocket.accept()
        printmsg("Accepted connection from %s" % str(address))
        server(socket, beeper)



if __name__ == "__main__":
    run()
