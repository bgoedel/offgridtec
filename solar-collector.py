#!/usr/bin/python3

import socket
import sys
import time
import os.path
import json
import threading


class Collector(object):
    def __init__(self, serverIp, serverPort, targetDir, intervalSecs):
        self.serverIp = serverIp
        self.serverPort = serverPort
        self.targetDir = targetDir
        self.filenamePrefix = targetDir.split("/")[-1]
        self.intervalSecs = intervalSecs

    def request(self, ip, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((ip, port))
            sock.sendall(bytes("read", 'ascii'))
            response = str(sock.recv(1024), 'ascii')
            print("Received: {}".format(response))
            return response

    def collect(self):
        threading.Timer(self.intervalSecs, self.collect).start()
        decoder = json.JSONDecoder()
        response = decoder.decode(self.request(self.serverIp, self.serverPort))
        responseKeys = list(response.keys())
        responseKeys.sort()
        filename = os.path.join(self.targetDir, "%s-%s.csv" % (self.filenamePrefix, time.strftime("%Y%m%d")))
        if os.path.exists(filename):
            f = open(filename, "a")
        else:
            f = open(filename, "w")
            f.write("time;%s\n" % ";".join(k for k in responseKeys))
        f.write("%s;" % time.strftime("%Y-%m-%d %H:%M:%S"))
        f.write("%s\n" % ";".join("%0.2f" % response[k] for k in responseKeys))
        f.close()

    def run(self):
        self.collect()


if __name__=="__main__":
    if len(sys.argv) != 4:
        sys.stderr.write("usage: %s <server> <targetDiry> <interval_secs>\n" % sys.argv[0])
        sys.stderr.write("   ex: %s 192.168.193.2:9992 /home/pi/offgridtec 60\n" % sys.argv[0])
        sys.exit(-1)
    serverIp = sys.argv[1].split(":")[0]
    serverPort = int(sys.argv[1].split(":")[1])
    targetDir = sys.argv[2]
    intervalSecs = int(sys.argv[3])
    collector = Collector(serverIp, serverPort, targetDir, intervalSecs)
    collector.run()
