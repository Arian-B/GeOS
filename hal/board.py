# hal/board.py

from hal.gpio import GPIOPin
from hal.i2c import I2CBus
from hal.spi import SPIBus
from hal.adc import ADCChannel


class Board:
    def gpio(self, pin, mode="IN"):
        return GPIOPin(pin, mode=mode)

    def i2c(self, bus_id=1):
        return I2CBus(bus_id=bus_id)

    def spi(self, bus_id=0, device_id=0):
        return SPIBus(bus_id=bus_id, device_id=device_id)

    def adc(self, channel=0):
        return ADCChannel(channel=channel)
