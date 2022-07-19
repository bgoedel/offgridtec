#!/usr/bin/python3

import serial
import sys
import traceback
import socketserver
import json
import time

telegram = {
    "chargerTemp": ([0xED, 0xDB], 2),
    "chargerErr": ([0xED, 0xDA], 1),
    "chargerCurrent": ([0xED, 0xD7], 2),
    "chargerVoltage": ([0xED, 0xD5], 2),
    "panelPower": ([0xED, 0xBC], 4),
    "panelVoltage": ([0xED, 0xBB], 2),
    "panelCurrent": ([0xED, 0xBD], 2),
    "trackerMode": ([0xED, 0xB3], 1)
}

global devName


def value(l):
    return (int(ord(l[0])) * 256 + int(ord(l[1]))) / 100.0


class VEdirect(object):
    def __init__(self, devName):
        try:
            self.dev = serial.Serial(devName, 19200, stopbits=1, bytesize=8)
            print("%s opened" % devName)
        except serial.SerialException as e:
            sys.stderr.write("problem with the VE.direct device: %s" % e)
            sys.exit(-1)

    def getU8(self, l):
        return (int(l[0], 16) << 4) + int(l[1], 16)

    def getU16(self, l):
        return (self.getU8(l[2:4]) << 8) + self.getU8(l[0:2])

    def getU32(self, l):
        return (self.getU16(l[4:8]) << 16) + self.getU16(l[0:4])

    def getRegister(self, registerName):
        t, resultLen = telegram[registerName]
        s = b":7%02X%02X%02X\n" % (t[1], t[0], 0x0255-(t[0]+t[1]+7))
        r = self.send(s)
        flags = self.getU8(r[6:8])
        if flags == 0:
            value = self.getU8(r[8:10]) if resultLen == 1 \
                else self.getU16(r[8:12]) if resultLen == 2\
                else self.getU32(r[8:16])
            return value
        else:
            return -1

    def send(self, telegram):
        self.dev.write(telegram)
        # print("-> 0x%02X" % b)
        response = []
        frameStarted = False
        while True:
            try:
                b = self.dev.read(1)
                if b == b":":
                    frameStarted = True
                    response = [b":"]
                elif frameStarted and (b == b"\n"):
                    if response[1] != b"7":
                        frameStarted = False
                    else:
                        break
                else:
                    response.append(b)
            except Exception as e:
                sys.stderr.write("exception: %s" % e)
                traceback.print_exc()
                break
        return response

    def close(self):
        self.dev.close()


# print("%s closed" % self.dev)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, serverAddr, handler):
        self.allow_reuse_address = True
        super().__init__(serverAddr, handler)


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.recv(1024)
        veDirect = VEdirect(sys.argv[1])
        enc = json.JSONEncoder()
#        electricParameters = ElectricParameters(veDirect.send(telegram["getElectricParameters"][0]))
#        temperatureParameter = TemperatureParameters(veDirect.send(telegram["getTemperatures"][0]))
#        self.request.sendall(enc.encode({
#            "battVoltage": electricParameters.getBatteryVoltage(),
#            "outVoltage": electricParameters.getOutVoltage(),
#            "outCurrent": electricParameters.getOutCurrent(),
#            "outPower": electricParameters.getOutPower(),
#            "temperature": temperatureParameter.getTemperature()
#        }).encode())
#        rs485.close()


def main():
    if len(sys.argv) != 3:
        sys.stderr.write("usage: %s <dev> <portNr>\n" % sys.argv[0])
        sys.stderr.write("   ex: %s /dev/ttyUSB0 9993\n" % sys.argv[0])
        sys.exit(-1)
    devName = sys.argv[1]
    portNr = int(sys.argv[2])
    while True:
        try:
            server = ThreadedTCPServer(("", portNr), Handler)
            server.serve_forever()
        except Exception as exc:
            sys.stderr.write("Exception: %s" % exc)
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    veDirect = VEdirect("/dev/ttyUSB1")
    for regName in telegram.keys():
        print("%s: %s" % (regName, veDirect.getRegister(regName)))
    veDirect.close()
