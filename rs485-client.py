#!/usr/bin/python3

import socket
import sys

def client(ip, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        sock.sendall(bytes("read", 'ascii'))
        response = str(sock.recv(1024), 'ascii')
        print("Received: {}".format(response))


if __name__=="__main__":
    client(sys.argv[1], int(sys.argv[2]))