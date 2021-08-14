import sys
import os
import threading
import socket
import time
import uuid
import datetime
import struct

ANSI_RESET = "\u001B[0m"
ANSI_RED = "\u001B[31m"
ANSI_GREEN = "\u001B[32m"
ANSI_YELLOW = "\u001B[33m"
ANSI_BLUE = "\u001B[34m"

_NODE_UUID = str(uuid.uuid4())[:8]


def print_yellow(msg):
    print(f"{ANSI_YELLOW}{msg}{ANSI_RESET}")


def print_blue(msg):
    print(f"{ANSI_BLUE}{msg}{ANSI_RESET}")


def print_red(msg):
    print(f"{ANSI_RED}{msg}{ANSI_RESET}")


def print_green(msg):
    print(f"{ANSI_GREEN}{msg}{ANSI_RESET}")


def get_broadcast_port():
    return 35498


def get_node_uuid():
    return _NODE_UUID


class NeighborInfo(object):

    def __init__(self, delay, broadcast_count, ip=None, tcp_port=None):
        # Ip and port are optional, if you want to store them.

        self.delay = delay

        self.broadcast_count = broadcast_count

        self.ip = ip

        self.tcp_port = tcp_port


neighbor_information = {}


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_address = ("", 0)
server.bind(server_address)
server.listen(50)

broadcaster = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
broadcaster.bind(("", get_broadcast_port()))


def send_broadcast_thread():
    node_uuid = get_node_uuid()
    msg = node_uuid + ' ON ' + str(server.getsockname()[1])
    print('my tcp port ' + str(server.getsockname()[1]))
    while True:
        broadcaster.sendto(msg.encode('utf-8'), ('<broadcast>', get_broadcast_port()))
        time.sleep(1)


def receive_broadcast_thread():
    while True:
        data, (ip, port) = broadcaster.recvfrom(4096)
        uuid = data[:8].decode('utf-8')
        tcp_port = int(data[12:].decode('utf-8'))

        if uuid != get_node_uuid():
            if uuid in neighbor_information:
                if neighbor_information[uuid].broadcast_count < 10:
                    neighbor_information[uuid].broadcast_count += 1
                    print_blue(f"RECV: {data} FROM: {ip}:{port}")
                else:
                    neighbor_information[uuid].broadcast_count = 1
                    print_blue(f"RECV: {data} FROM: {ip}:{port}")
                    th3 = daemon_thread_builder(exchange_timestamps_thread, args=(uuid, ip, tcp_port))

            else:
                neighbor = NeighborInfo(None, 1, ip, tcp_port)
                neighbor_information[uuid] = neighbor
                th3 = daemon_thread_builder(exchange_timestamps_thread, args=(uuid, ip, tcp_port))


def tcp_server_thread():
    while True:
        connection, address = server.accept()
        connection.send(str(datetime.datetime.utcnow().timestamp()).encode('utf-8'))
        connection.close()


def exchange_timestamps_thread(other_uuid: str, other_ip: str, other_tcp_port: int):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        print_yellow(f"ATTEMPTING TO CONNECT TO {other_uuid}")
        time.sleep(3)
        client.connect((other_ip, other_tcp_port))
        other_timestamp = float(client.recv(4096).decode('utf-8'))
        current_timestamp = datetime.datetime.utcnow().timestamp()
        other_delay = current_timestamp - other_timestamp
        print_red('the old delay: ' + str(neighbor_information[other_uuid].delay))
        neighbor_information[other_uuid].delay = other_delay
        print_red('the new delay: ' + str(neighbor_information[other_uuid].delay))
        client.close()
        
    except ConnectionRefusedError:
        print('The node ' + other_uuid + ' that you try to connect has left...')
        neighbor_information.pop(other_uuid)


def daemon_thread_builder(target, args=()) -> threading.Thread:
    th = threading.Thread(target=target, args=args)
    th.setDaemon(True)
    th.start()
    return th


def entrypoint():
    th1 = daemon_thread_builder(send_broadcast_thread, args=())
    th2 = daemon_thread_builder(receive_broadcast_thread, args=())
    th4 = daemon_thread_builder(tcp_server_thread, args=())
    th1.join()
    th2.join()
    th4.join()


def main():
    print("*" * 50)
    print_red("To terminate this program use: CTRL+C")
    print_red("If the program blocks/throws, you have to terminate it manually.")
    print_green(f"NODE UUID: {get_node_uuid()}")
    print("*" * 50)
    time.sleep(2)  # Wait a little bit.
    entrypoint()


if __name__ == "__main__":
    main()
