#!/usr/bin/python3

import serial
import sys
import traceback
import socketserver
import json
import time

global devName

telegram = {
	"telegram1": ([0x03, 0x04, 0x32, 0x02, 0x00, 0x01, 0x9F, 0x50], [0x03, 0x04, 0x02, 0x00, 0x01, 0x01, 0x30]),
	"getElectricParameters": ([0x03, 0x43, 0x31, 0x08, 0x00, 0x08, 0xCB, 0x1F], [0x03, 0x43, 0x10, 0xFF]),
	"getTemperatures": ([0x03, 0x43, 0x31, 0x11, 0x00, 0x03, 0x5B, 0x1F], [0x03, 0x43, 0x06, 0x07]),
	"getThresholds": ([0x03, 0x43, 0x90, 0x30, 0x00, 0x04, 0x69, 0x2B], [0x03, 0x43, 0x08, 0x0F]),
	"telegram5": ([0x03, 0x01, 0x00, 0x11, 0x00, 0x01, 0xAC, 0x2D], [0x03, 0x01, 0x01, 0x00, 0x50, 0x30]),
	"telegram6": ([0x03, 0x01, 0x00, 0x0F, 0x00, 0x01, 0xCC, 0x2B], [0x03, 0x01, 0x01, 0x01, 0x91, 0xF0]),
	"telegram7": ([0x03, 0x01, 0x00, 0x04, 0x00, 0x01, 0xBD, 0xE9], [0x03, 0x01, 0x01, 0x00, 0x50, 0x30])
}


def value(l):
	return (int(ord(l[0])) * 256 + int(ord(l[1]))) / 100.0


class ElectricParameters(object):
	def __init__(self, telegram):
		self.telegram = telegram

	def getBatteryVoltage(self):
		return value(self.telegram[4:])

	def getOutVoltage(self):
		return value(self.telegram[12:])

	def getOutCurrent(self):
		return value(self.telegram[14:])

	def getOutPower(self):
		return value(self.telegram[16:])


class TemperatureParameters(object):
	def __init__(self, telegram):
		self.telegram = telegram

	def getTemperature(self):
		return value(self.telegram[4:])


class Thresholds(object):
	def __init__(self, telegram):
		self.telegram = telegram

	def getUnderVoltageThreshold(self):
		return value(self.telegram[4:])

	def getUnderVoltageRecovery(self):
		return value(self.telegram[6:])

	def getOvervoltageRecovery(self):
		return value(self.telegram[8:])

	def getOverVoltageThreshold(self):
		return value(self.telegram[10:])


class Rs485(object):
	def __init__(self, devName):
		try:
			self.dev = serial.Serial(devName, 115200, stopbits=2, bytesize=8, timeout=0.2)
			#print("%s opened" % devName)
		except serial.SerialException as exc:
			sys.stderr.write("problem with the RS485 device: %s" % exc)
			sys.exit(-1)

	def send(self, telegram):
		for b in telegram:
			self.dev.write(b"%c" % b)
			#print("-> 0x%02X" % b)
		response = []
		while True:
			try:
				b = self.dev.read(1)
				if (b is None):
					print("None")
					break
				if len(b) == 0:
					break
				#print("<- 0x%02X" % int(ord(b)))
				response.append(b)
			except Exception as exc:
				sys.stderr.write("exception: %s" % exc)
				traceback.print_exc()
				break
		return response

	def close(self):
		self.dev.close()
		#print("%s closed" % self.dev)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
	def __init__(self, serverAddr, handler):
		self.allow_reuse_address = True
		super().__init__(serverAddr, handler)


class Handler(socketserver.BaseRequestHandler):
	def handle(self):
		self.request.recv(1024)
		rs485 = Rs485(sys.argv[1])
		enc = json.JSONEncoder()
		electricParameters = ElectricParameters(rs485.send(telegram["getElectricParameters"][0]))
		temperatureParameter = TemperatureParameters(rs485.send(telegram["getTemperatures"][0]))
		self.request.sendall(enc.encode({
			"battVoltage": electricParameters.getBatteryVoltage(),
			"outVoltage": electricParameters.getOutVoltage(),
			"outCurrent": electricParameters.getOutCurrent(),
			"outPower": electricParameters.getOutPower(),
			"temperature": temperatureParameter.getTemperature()
		}).encode())
		rs485.close()


if __name__=="__main__":
	if len(sys.argv) != 3:
		sys.stderr.write("usage: %s <dev> <portNr>\n" % sys.argv[0])
		sys.stderr.write("   ex: %s /dev/ttyUSB0 9992\n" % sys.argv[0])
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
