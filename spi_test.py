#! /usr/bin/python3

# This scripts assumes that an appropriate MCP3208 board is attached to
# the RPi running this script.

# The MCP3204/8 uses the SPI bus but in a little "special" way.
# To accommodate this, we need to handle transmissions like so:
# 5 leading 0s, followed by a 1 (artificial start bit) followed by
# a 1/0 for single-ended / differential respectively
# 3-bit channel number broken up as 
# D2
# then the next 8 bits starts with D1, D0 followed by 6 bits of don't cares and
# another byte of don't cares (X).
# The data is shifted in after clock pulse 13 
# This looks something like:
#
# |      |        packet 0          |           packet 1           |        packet 2         |
# |------|--------------------------|------------------------------|-------------------------|
# | bit  |   7 6 5 4 3  2   1   0   | 7   6   5  4  3   2   1   0  | 7  6  5  4  3  2  1  0  |
# | MOSI |   0 0 0 0 0  SB SE/D CA2 | CA1 CA0 X  X  X   X   X   X  | X  X  X  X  X  X  X  X  |
# | MISO |   - - - - -  -   -   -   |  -  -  -  N  D11 D10 D9  D8  | D7 D6 D5 D4 D3 D2 D1 D0 |
#
# Where
# SB = Start bit
# SE/D is Single Ended(1) or differential(0)
# CAx is the Channel Address (0-7)
# N = NULL bit
# Dx = Data bit x
#

import spidev
import time
"""
SPI Test 
--------
Script for reading channel 0 of an MCP320X ADC attached to SPI0/CE0 of the
Raspberry Pi header pins. It loops for 1000 iterations with 1 second intervals
between reads.
Be sure that spidev-py is installed and that the SPI0 overlay is enabled. 
"""

spi=spidev.SpiDev(0,0)
spi.mode = 0

# Single-ended channel 0 is coded as SE D2 D1 D0 = 1000
# however this is split across the first two bytes as:
# 0000 0110 00XX XXXX XXXX
# See header notes for more info.

for x in range(0,1000):
    ch0 = [0x06, 0x00, 0x00]
    rcvd = spi.xfer(ch0, 500000)
    val = ((rcvd[1] & 0x0F) << 8) + rcvd[2]
    # Correct val as code = (4096 * Vin) / Vref 
    # Our Vref is 5V and we are offset by +2.5V so... Vin = val * Vref / 4096 - 2.5
    val = val * 5 / 4096 - 2.5

    print(f"Received {rcvd} = {val:0.2f}")
    time.sleep(1)

spi.close()


