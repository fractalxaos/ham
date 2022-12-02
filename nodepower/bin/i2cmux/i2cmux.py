#!/usr/bin/python3
#
# Module: tmp102.py
#
# Description: This module acts as an interface between the TCA9548A i2c mux
# and connected devices.  Class methods send and receive data from specific
# devices connected to the mux. It acts as a library module that
# can be imported into and called from other Python programs.
#
# Copyright 2022 Jeff Owrey
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
#   * v10 released 16 March 2022 by J L Owrey; first release
#
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

# Import the I2C interface library
import smbus
import time

# Define default sm bus address.
DEFAULT_BUS_ADDRESS = 0x70
DEFAULT_BUS_NUMBER = 1

# Define the default mux configuration.  See the TCA9548A data sheet
# for meaning of each bit.  The following byte is written to the
# configuration register.  This byte disables all mux outputs.
#     byte 1: 00000000
DEFAULT_CONFIG = 8

channel_conf=[0b00000001,0b00000010,0b00000100,0b00001000,0b00010000, \
              0b00100000,0b01000000,0b10000000,0]

class i2cmux:

    # Initialize the TCA9548A multiplexer at the supplied address
    # (default address is 0x70), and supplied bus (default is 1).
    # Creates a new SMBus object for each instance of this class.
    # Writes configuration data (one byte) to the TCA9548A configuration
    # register.
    def __init__(self, mAddr=DEFAULT_BUS_ADDRESS,
                 sbus=DEFAULT_BUS_NUMBER,
                 config=DEFAULT_CONFIG,
                 debug=False): 
        # Instantiate a smbus object
        self.muxAddr = mAddr
        self.bus = smbus.SMBus(sbus)
        self.debugMode = debug

        # Initialize mux with all channels disabled.  
        self.bus.write_byte(self.muxAddr, channel_conf[config])

        if self.debugMode:
            # Read the mux configuration register.
            data = self.getInfo()
            print("mux config register: %s\n" % data)
    ## end def

    # Reads the configuration register (two bytes).
    def getInfo(self):
        # Read configuration data
        config = self.bus.read_byte(self.muxAddr)
        configB = format(config, "08b")
        return (configB)
    ## end def

    def write_i2c_block_data(self, channel, addr, offset, data):
        # Write block data to the device connected to the specified
        # channel.
        # Enable the specified mux channel.  
        self.bus.write_byte(self.muxAddr, channel_conf[channel])
        time.sleep(.001)
        # Write data to the device connected to the channel.     
        self.bus.write_i2c_block_data(addr, offset, data)
        time.sleep(.001)
        # Disable the mux channel.
        self.bus.write_byte(self.muxAddr, 0)
    ## end def

    def read_i2c_block_data(self, channel, addr, offset, nBytes):
        # Read block data from the device connected to the specified
        # channel.

        # Enable the specified mux channel.  
        self.bus.write_byte(self.muxAddr, channel_conf[channel])
        time.sleep(.001)
        # Write data to the device connected to the channel.     
        data = self.bus.read_i2c_block_data(addr, offset, nBytes)
        time.sleep(.001)
        # Disable the mux channel.
        self.bus.write_byte(self.muxAddr, 0)
        return data
    ## end def

    def write_byte(self, channel, addr, byte):
        # Write a byte to the device connected to the specified
        # channel.

        # Enable the specified mux channel.  
        self.bus.write_byte(self.muxAddr, channel_conf[channel])
        time.sleep(.001)
        # Write data to the device connected to the channel.     
        self.bus.write_byte(addr, byte)
        time.sleep(.001)
        # Disable the mux channel.
        self.bus.write_byte(self.muxAddr, 0)
    ## end def

    def read_byte(self, channel, addr):
        # Read a byte from the device connected to the specified
        # channel.

        # Enable the specified mux channel.  
        self.bus.write_byte(self.muxAddr, channel_conf[channel])
        time.sleep(.001)
        # Read data from the device connected to the channel.     
        byte = self.bus.read_byte(addr)
        time.sleep(.001)
        # Disable the mux channel.
        self.bus.write_byte(self.muxAddr, 0)
        return byte
    ## end def

## end class

def testclass():
    # Initialize the smbus and TMP102 sensor.
    ts1 = i2cmux(0x70, 1, config=0, debug=True)
    ts2 = i2cmux(debug=True)
    del ts1, ts2
## end def

if __name__ == '__main__':
    testclass()

