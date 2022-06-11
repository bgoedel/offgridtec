#!/usr/bin/python3

import serial
import crcmod
import sys
import time
import traceback

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
			self.dev = serial.Serial(devName, 115200, stopbits=2, bytesize=8, timeout=1)
		except serial.SerialException as exc:
			self.log("problem with the RS485 device: " + exc.message)
			self.logger.stop()
			sys.exit(-1)

	def send(self, telegram):
		for b in telegram:
			self.dev.write(b"%c" % b)
			print("-> 0x%02X  -->  0x%02X" % (b, b))
		response = []
		while True:
			try:
				b = self.dev.read(1)
				if (b is None):
					print("None")
					break
				if len(b) == 0:
					break
				print("<- 0x%02X" % int(ord(b)))
				response.append(b)
			except Exception as exc:
				print("exception: %s" % exc)
				traceback.print_exc()
				break
		return response

	def close(self):
		self.dev.close()

	def reverse(self, b):
		c = 0
		if b & 0x01:
			c |= 0x80
		if b & 0x02:
			c |= 0x40
		if b & 0x04:
			c |= 0x20
		if b & 0x08:
			c |= 0x10
		if b & 0x10:
			c |= 0x08
		if b & 0x20:
			c |= 0x04
		if b & 0x40:
			c |= 0x02
		if b & 0x80:
			c |= 0x01
		return c



if __name__=="__main__":
	rs485 = Rs485(sys.argv[1])
	print("open")
	response = rs485.send(telegram["getElectricParameters"][0])
	electricParameters = ElectricParameters(response)
	print("Batterie: %5.2f V" % electricParameters.getBatteryVoltage())
	print("Ausgangsspannung: %6.2f V" % electricParameters.getOutVoltage())
	print("Ausgangsstrom: %4.2f A" % electricParameters.getOutCurrent())
	print("AUsgangsleistung: %6.2f W" % electricParameters.getOutPower())
	response = rs485.send(telegram["getTemperatures"][0])
	temperatureParameter = TemperatureParameters(response)
	print("Temperatur: %5f °C" % temperatureParameter.getTemperature())
	rs485.close()