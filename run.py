import socket
import sys
from beeper.beeper import Beeper
from beeper.chopper import Chopper
from beeper.socket_io import SocketIO
from beeper.event_message_received import EventMessageReceived
from beeper.bgp_message import BgpMessage, parse_bgp_message

BGP_PORT = 179
ADDRESS = '0.0.0.0'

def printmsg(msg):
    sys.stderr.write("%s\n" % msg)
    sys.stderr.flush()

def server(socket, beeper):
    input_stream = SocketIO(socket)
    chopper = Chopper(input_stream)

    while True:
        printmsg("Receiving message from chopper")
        message_type, serialised_message = chopper.next()
        printmsg("Decoding message")
        message = parse_bgp_message(message_type, serialised_message)
        printmsg(str(message))
        printmsg("Sending event to beeper")
        event = EventMessageReceived(message)
        output_messages = beeper.event(event)
        printmsg("Messages from beeper: %s" % [str(x) for x in output_messages])
        # send them
        for message in output_messages:
            socket.send(BgpMessage.pack(message))


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
        server(clientsocket, beeper)
        clientsocket.shutdown(socket.SHUT_RDWR)
        clientsocket.close()
        break

    serversocket.shutdown(socket.SHUT_RDWR)
    serversocket.close()

if __name__ == "__main__":
    run()
