# hal/__init__.py

from hal.board import Board
from hal.gpio import GPIOPin
from hal.i2c import I2CBus
from hal.spi import SPIBus
from hal.adc import ADCChannel

__all__ = ["Board", "GPIOPin", "I2CBus", "SPIBus", "ADCChannel"]
