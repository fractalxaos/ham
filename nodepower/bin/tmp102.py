#!/usr/bin/python
#
# Module: tmp102.py
#
# Description: This module acts as an interface between the TMP102 sensor
# and downstream applications that use the data.  Class methods get
# temperature data from the TMP102 sensor. It acts as a library module that
# can be imported into and called from other Python programs.
#
# Copyright 2021 Jeff Owrey
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/license.
#
# Revision History
#   * v10 released 01 June 2021 by J L Owrey; first release
#
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

# Import the I2C interface library
import smbus
import time

# Define constants
DEGSYM = u'\xb0'

# Define TMP102 Device Registers
CONFIG_REG = 0x1
TEMP_REG = 0x0

class tmp102:

    # Initialize the TMP102 sensor at the supplied address (default
    # address is 0x48), and supplied bus (default is 1).  Creates
    # a new SMBus object for each instance of this class.  Writes
    # configuration data (two bytes) to the TMP102 configuration
    # register.
    def __init__(self, sAddr=0x48, sbus=1): 
        # Instantiate a smbus object
        self.sensorAddr = sAddr
        self.bus = smbus.SMBus(sbus)
        # Initialize TMP102 sensor.  See the data sheet for meaning of
        # each bit.  The following bytes are written to the configuration
        # register
        #     byte 1: 01100000
        #     byte 2: 10100000
        initData = [0x60, 0xA0]
        self.bus.write_i2c_block_data(self.sensorAddr, CONFIG_REG, initData)
    ## end def

    # Reads the configuration register (two bytes).
    def status(self):
        # Read configuration data
        config = self.bus.read_i2c_block_data(self.sensorAddr, CONFIG_REG, 2)
        configB1 = format(config[0], "08b")
        configB2 = format(config[1], "08b")
        return (configB1, configB2)
    ## end def

    def getTempReg(self):
        # Read temperature register and return raw binary data for test
        # and debug.
        data = self.bus.read_i2c_block_data(self.sensorAddr, TEMP_REG, 2)
        dataB1 = format(data[0], "08b")
        dataB2 = format(data[1], "08b")
        return (dataB1, dataB2)
    ## end def

    # Gets the temperature in binary format and converts to degrees
    # Celsius.
    def getTempC(self):
        # Get temperature data from the sensor.
        # TMP102 returns the data in two bytes formatted as follows
        #        -------------------------------------------------
        #    bit | b7  | b6  | b5  | b4  | b3  | b2  | b1  | b0  |
        #        -------------------------------------------------
        # byte 1 | d11 | d10 | d9  | d8  | d7  | d6  | d5  | d4  |
        #        -------------------------------------------------
        # byte 2 | d3  | d2  | d1  | d0  | 0   |  0  |  0  |  0  |
        #        -------------------------------------------------
        # The temperature is returned in d11-d0, a two's complement,
        # 12 bit number.  This means that d11 is the sign bit.
        data=self.bus.read_i2c_block_data(self.sensorAddr, TEMP_REG, 2)
        # Format into a 12 bit word.
        bData = ( data[0] << 8 | data[1] ) >> 4
        # Convert from two's complement to integer.
        # If d11 is 1, the the number is a negative two's complement
        # number.  The absolute value is 2^12 - 1 minus the value
        # of d10-d0 taken as a positive number.
        if bData > 0x7FF:  # all greater values are negative numbers
            bData = -(0xFFF - bData)  # 0xFFF is 2^12 - 1
        # convert integer data to Celsius
        tempC = bData * 0.0625 # LSB is 0.0625 deg Celsius
        return tempC
    ## end def

    def getTempF(self):
        # Convert Celsius to Fahrenheit using standard formula.
        tempF = (9./5.) * self.getTempC() + 32.
        return tempF
    ## end def
## end class

def testclass():
    # Initialize the smbus and TMP102 sensor.
    ts1 = tmp102(0x48, 1)
    # Read the TMP102 configuration register.
    data = ts1.status()
    print "configuration register: %s %s\n" % data
    # Print out sensor values.
    bAl = False
    while True:
        regdata = ts1.getTempReg()
        tempC = ts1.getTempC()
        tempF = ts1.getTempF()
        if bAl:
            bAl = False
            print "\033[42;30mTemperature Reg: %s %s\033[m" % regdata
            print "\033[42;30m%6.2f%sC  %6.2f%s                 \033[m" % \
                  (tempC, DEGSYM, tempF, DEGSYM)
        else:
            bAl = True
            print "Temperature Reg: %s %s" % regdata
            print "%6.2f%sC  %6.2f%sF" % \
                  (tempC, DEGSYM, tempF, DEGSYM)
        time.sleep(2)
    ## end while
## end def

if __name__ == '__main__':
    testclass()

