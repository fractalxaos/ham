#!/usr/bin/python3 -u
#
# Module: ina260.py
#
# Description: This module acts as an interface between the INA260 sensor
# and downstream applications that use the data.  Class methods get
# current, voltage, and power data from the INA260 sensor.  It acts as a
# library module that can be imported into and called from other Python
# programs.
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

# Define Device Registers
CONFIG_REG = 0x0
ID_REG = 0xFE
CUR_REG = 0x1
VOLT_REG = 0x2
PWR_REG = 0x3

# Define default sm bus address.
DEFAULT_BUS_ADDRESS = 0x40
DEFAULT_BUS_NUMBER = 1

# Define the default sensor configuration.  See the INA260 data sheet
# for meaning of each bit.  The following bytes are written to the
# configuration register
#     byte 1: 11100000
#     byte 2: 00100111
DEFAULT_CONFIG = 0xE027

class ina260:
    # Initialize the INA260 sensor at the supplied address (default
    # address is 0x40), and supplied bus (default is 1).  Creates
    # a new SMBus object for each instance of this class.  Writes
    # configuration data (two bytes) to the INA260 configuration
    # register.
    def __init__(self, sAddr=DEFAULT_BUS_ADDRESS,
                       sbus=DEFAULT_BUS_NUMBER,
                       config=DEFAULT_CONFIG,
                       debug=False):
        # Instantiate a smbus object.
        self.sensorAddr = sAddr
        self.bus = smbus.SMBus(sbus)
        self.debugMode = debug

        # Initialize INA260 sensor.  
        initData = [(config >> 8), (config & 0x00FF)]
        self.bus.write_i2c_block_data(self.sensorAddr, CONFIG_REG, initData)

        if self.debugMode:
            data = self.getInfo()
            print(self)
            print("manufacturer ID: %s %s\n"\
                  "INA260 configuration register: %s %s\n" % data)
    ## end def

    def getInfo(self):
        # Read manufacture identification data.
        mfcid = self.bus.read_i2c_block_data(self.sensorAddr, ID_REG, 2)
        mfcidB1 = format(mfcid[0], "08b")
        mfcidB2 = format(mfcid[1], "08b")
        # Read configuration data.
        config = self.bus.read_i2c_block_data(self.sensorAddr, CONFIG_REG, 2)
        configB1 = format(config[0], "08b")
        configB2 = format(config[1], "08b")
        return (mfcidB1, mfcidB2, configB1, configB2)
    ## end def

    def getCurrentReg(self):
        # Read current register and return raw binary data for test and
        # debug.
        data = self.bus.read_i2c_block_data(self.sensorAddr, CUR_REG, 2)
        dataB1 = format(data[0], "08b")
        dataB2 = format(data[1], "08b")
        return (dataB1, dataB2)
    ## end def

    def getCurrent(self):
        # Get the current data from the sensor.
        # INA260 returns the data in two bytes formatted as follows
        #        -------------------------------------------------
        #    bit |  7  |  6  |  5  |  4  |  3  |  2  |  1  |  0  |
        #        -------------------------------------------------
        # byte 1 | d15 | d14 | d13 | d12 | d11 | d10 | d9  | d8  |
        #        -------------------------------------------------
        # byte 2 | d7  | d6  | d5  | d4  | d3  |  d2 | d1  | d0  |
        #        -------------------------------------------------
        # The current is returned in d15-d0, a two's complement,
        # 16 bit number.  This means that d15 is the sign bit.        
        data=self.bus.read_i2c_block_data(self.sensorAddr, CUR_REG, 2)

        if self.debugMode:
            dataB1 = format(data[0], "08b")
            dataB2 = format(data[1], "08b")
            print("current register: %s %s" % (dataB1, dataB2))

        # Format into a 16 bit word.
        bdata = data[0] << 8 | data[1]
        # Convert from two's complement to integer.
        # If d15 is 1, the the number is a negative two's complement
        # number.  The absolute value is 2^16 - 1 minus the value
        # of d15-d0 taken as a positive number.
        if bdata > 0x7FFF:
            bdata = -(0xFFFF - bdata) # 0xFFFF equals 2^16 - 1
        # Convert integer data to mAmps.
        mAmps = bdata * 1.25  # LSB is 1.25 mA
        return mAmps
    ## end def

    def getVoltageReg(self):
        # Read voltage register and return raw binary data for test
        # and debug.
        data = self.bus.read_i2c_block_data(self.sensorAddr, VOLT_REG, 2)
        dataB1 = format(data[0], "08b")
        dataB2 = format(data[1], "08b")
        return (dataB1, dataB2)
    ## end def

    def getVoltage(self):
        # Get the voltage data from the sensor.
        # INA260 returns the data in two bytes formatted as follows
        #        -------------------------------------------------
        #    bit |  7  |  6  |  5  |  4  |  3  |  2  |  1  |  0  |
        #        -------------------------------------------------
        # byte 1 | d15 | d14 | d13 | d12 | d11 | d10 | d9  | d8  |
        #        -------------------------------------------------
        # byte 2 | d7  | d6  | d5  | d4  | d3  |  d2 | d1  | d0  |
        #        -------------------------------------------------
        # The voltage is returned in d15-d0 as an unsigned integer.
        data=self.bus.read_i2c_block_data(self.sensorAddr, VOLT_REG, 2)

        if self.debugMode:
            dataB1 = format(data[0], "08b")
            dataB2 = format(data[1], "08b")
            print("voltage register: %s %s" % (dataB1, dataB2))

        # Convert data to volts.
        volts = (data[0] << 8 | data[1]) * 0.00125 # LSB is 1.25 mV
        return volts
    ## end def

    def getPower(self):
        # Get the wattage data from the sensor.
        # INA260 returns the data in two bytes formatted as follows
        #        -------------------------------------------------
        #    bit | 7   |  6  |  5  |  4  |  3  |  2  |  1  |  0  |
        #        -------------------------------------------------
        # byte 1 | d15 | d14 | d13 | d12 | d11 | d10 | d9  | d8  |
        #        -------------------------------------------------
        # byte 2 | d7  | d6  | d5  | d4  | d3  |  d2 | d1  | d0  |
        #        -------------------------------------------------
        # The wattage is returned in d15-d0 as an unsigned integer.
        data=self.bus.read_i2c_block_data(self.sensorAddr, PWR_REG, 2)

        if self.debugMode:
            dataB1 = format(data[0], "08b")
            dataB2 = format(data[1], "08b")
            print("power register: %s %s" % (dataB1, dataB2))

        # Convert data to milliWatts. 
        mW = (data[0] << 8 | data[1]) * 10.0  # LSB is 10.0 mW
        return mW
   ## end def
## end class

def test():
    # Initialize the smbus and INA260 sensor.
    pwr1 = ina260(0x40, 1, debug=True)
    # Print out sensor values.
    while True:
        print("%6.2f mA" % pwr1.getCurrent())
        print("%6.2f V" % pwr1.getVoltage())
        print("%6.2f mW\n" % pwr1.getPower())
        time.sleep(2)
## end def

if __name__ == '__main__':
    test()

