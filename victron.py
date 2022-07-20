#!/usr/bin/python3

import serial
import sys
import traceback
import socketserver
import json
import time

telegram = {
    "chargerTemp": ([0xED, 0xDB], 2, 100, "°C"),
    "chargerErr": ([0xED, 0xDA], 1, 0,
                   {
                        0: "no error",
                        2: "Battery voltage too high",
                        17: "Charger internal temperature too high",
                        18: "Charger excessive output current",
                        19: "Charger current polarity reversed",
                        20: "Charger bulk time expired (when 10 hour bulk time protection active)",
                        21: "Charger current sensor issue (bias not within expected limits during off state)",
                        26: "Charger terminals overheated",
                        28: "Converter issue (dual converter models, one of the converters is not working)",
                        33: "Input voltage too high",
                        34: "Input excessive current",
                        38: "Input shutdown (due to excessive battery voltage)",
                        39: "Input shutdown (current flowing while the converter is switched off)",
                        66: "Incompatible device in the network (for synchronized charging)",
                        67: "BMS connection lost",
                        68: "Network misconfigured (e.g. combining ESS with ve.smart networking)",
                        116: "Calibration data lost",
                        117: "Incompatible firmware (i.e. not for this model)",
                        119: "Settings data invalid / corrupted (use restore to defaults and reset to recover)"
                    }),
    "chargerCurrent": ([0xED, 0xD7], 2, 10, "A"),
    "chargerVoltage": ([0xED, 0xD5], 2, 100, "V"),
    "panelPower": ([0xED, 0xBC], 4, 100, "W"),
    "panelVoltage": ([0xED, 0xBB], 2, 100, "V"),
    "panelCurrent": ([0xED, 0xBD], 2, 10, "A"),
    "trackerMode": ([0xED, 0xB3], 1, 0,
                    {
                        0: "off",
                        1: "voltage/current limited",
                        2: "MPPT tracker"
                    }),
    "deviceMode": ([0x02, 0x00], 1, 0,
                   {
                       0: "Charger off",
                       1: "Charger on",
                       4: "Charger off"
                   }),
    "deviceState": ([0x02, 0x01], 1, 0,
                    {
                        0: "Not charging",
                        2: "Failure",
                        3: "Bulk",
                        4: "Absorption",
                        5: "Float",
                        7: "Voltage controlled with equalisation voltage set-point",
                        245: "The device is about to start (signal to external control)",
                        247: "Voltage controlled with equalisation voltage set-point",
                        252: "Voltage controlled with remote voltage set-point",
                        255: "No information available"
                    })
}

global devName
global portNr


def value(l):
    return (int(ord(l[0])) * 256 + int(ord(l[1]))) / 100.0


class VEdirect(object):
    def __init__(self, devName):
        try:
            self.dev = serial.Serial(devName, 19200, stopbits=1, bytesize=8)
        except serial.SerialException as e:
            sys.stderr.write("problem with the VE.direct device: %s" % e)
            sys.exit(-1)

    def getU8(self, l):
        return (int(l[0], 16) << 4) + int(l[1], 16)

    def getU16(self, l):
        return (self.getU8(l[2:4]) << 8) + self.getU8(l[0:2])

    def getU32(self, l):
        return (self.getU16(l[4:8]) << 16) + self.getU16(l[0:4])

    def checksum(self, s):
        if s < 0x55:
            return 0x55 - s
        elif s < 0x155:
            return 0x155 - s
        elif s < 0x255:
            return 0x255 - s
        else:
            return 0x355 - s

    def getRegisterRaw(self, registerName):
        t, resultLen, factor, text = telegram[registerName]
        s = b":7%02X%02X00%02X\n" % (t[1], t[0], self.checksum(t[0]+t[1]+7))
        r = self.send(s)
        flags = self.getU8(r[6:8])
        if flags == 0:
            value = self.getU8(r[8:10]) if resultLen == 1 \
                else self.getU16(r[8:12]) if resultLen == 2 \
                else self.getU32(r[8:16])
            if factor != 0:
                return value/float(factor)
            else:
                return int(value)
        else:
            return -65535

    def getRegister(self, registerName):
        t, resultLen, factor, text = telegram[registerName]
        value = self.getRegisterRaw(registerName)
        if value != -65535:
            if factor != 0:
                return "%.2f %s" % (value, text)
            else:
                return text[value]
        else:
            return "couldn't read"

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


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, serverAddr, handler):
        self.allow_reuse_address = True
        super().__init__(serverAddr, handler)


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.recv(1024)
        veDirect = VEdirect(devName)
        enc = json.JSONEncoder()
        data = {}
        for regName in telegram.keys():
            data[regName] = veDirect.getRegisterRaw(regName)
        self.request.sendall(enc.encode(data).encode())
        veDirect.close()


def main():
    while True:
        try:
            server = ThreadedTCPServer(("", portNr), Handler)
            server.serve_forever()
        except Exception as exc:
            sys.stderr.write("Exception: %s" % exc)
            traceback.print_exc()
            time.sleep(5)

def interactive():
    veDirect = VEdirect(sys.argv[1])
    for regName in telegram.keys():
        print("%s: %s" % (regName, veDirect.getRegister(regName)))
    veDirect.close()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        devName = sys.argv[1]
        interactive()
    elif len(sys.argv) == 3:
        devName = sys.argv[1]
        portNr = int(sys.argv[2])
        main()
    else:
        sys.stderr.write("usage: %s <dev> <portNr>\n" % sys.argv[0])
        sys.stderr.write("   ex: %s /dev/ttyUSB0 9993\n" % sys.argv[0])
        sys.exit(-1)
