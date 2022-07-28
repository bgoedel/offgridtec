#!/usr/bin/python3

import socket
import json
import threading

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS


class Collector(object):
    def __init__(self, sourcesDict, intervalSecs, influxBridge):
        self.sourcesDict = sourcesDict
        self.intervalSecs = intervalSecs
        self.influxBridge = influxBridge
        self.jsonEnc = json.JSONEncoder()
        self.jsonDec = json.JSONDecoder()

    def collect(self):
        threading.Timer(self.intervalSecs, self.collect).start()
        dataLines = []
        for sourceName, dataSource in self.sourcesDict.items():
            data = self.jsonDec.decode(dataSource.request())
            for k,v in data.items():
                dataLines.append("solar,entity=%s %s=%f" % (sourceName, k, v))
        self.influxBridge.write(dataLines)

    def run(self):
        self.collect()


class DataSource(object):
    def __init__(self, serverIp, serverPort):
        self.serverIp = serverIp
        self.serverPort = serverPort

    def request(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.serverIp, self.serverPort))
            sock.sendall(bytes("read", 'ascii'))
            response = str(sock.recv(1024), 'ascii')
            return response


class InfluxBridge(object):
    def __init__(self):
        self.token = ""
        self.org = "org"
        self.bucket = "bucket"
        self.url = "http://10.18.0.1:8086"

    def write(self, data):
        with InfluxDBClient(url=self.url, token=self.token, org=self.org) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            write_api.write(self.bucket, self.org, data)
            client.close()


if __name__ == "__main__":
    inverterSource = DataSource("192.168.193.2", 9992)
    chargerSource = DataSource("192.168.193.2", 9993)
    Collector({"inverter": inverterSource, "charger": chargerSource}, 60, InfluxBridge()).run()
