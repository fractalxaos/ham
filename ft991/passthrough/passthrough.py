#!/usr/bin/python -u
# The -u option turns off block buffering of python output. This assures
# that output streams to stdout when output happens.
#
# Description:  This program passes commands from a command line prompt
#               directly through to the FT991.  Also a few utility macro
#               commands have been defined that can be typed on the 
#               command line.
#
# This script has been tested with the following
#
#     Python 2.7.15rc1 (default, Nov 12 2018, 14:31:15) 
#     [GCC 7.3.0] on linux2
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

import sys, serial, time

# Determine OS type and set device port accordingly.
OS_type = sys.platform
if 'WIN' in OS_type.upper():
    _SERIAL_PORT = 'COM5'
else:
    _SERIAL_PORT = '/dev/ttyUSB0'

# General constant defines
_BAUD_RATE = 9600
_INTERFACE_TIMEOUT = 0.1 # seconds
_SERIAL_READ_TIMEOUT = 0.1 # seconds
_SERIAL_READ_BUFFER_LENGTH = 1024 # characters

# Define functions encapsulating serial communications to and from
# a generic serial device object.

def getAnswer(device, termchar):
    """
    Description: Reads output one character at a time from the device
                 until a terminating character is received.  Returns a     
                 string containing the characters read from the serial
                 port.
    Parameters:  device - a serial object connected to the device port
                 termchar - character terminating the answer string
    Returns:     string
    """
    answer = '' # initialize answer string to empty string
    charCount = 0  # reset read character count to zero

    while True:
        startTime = time.time() # Start read character timer
        c =''
        while True:
            # Check for a character available in the serial read buffer.
            if device.in_waiting:
                c = device.read()
                break
            # Timeout if a character does not become available.
            if time.time() - startTime > _SERIAL_READ_TIMEOUT:
                break # Read character timer has timed out.
        # Return empty string if a character has not become available.
        if c == '':
            break;
        answer += c # Form a string from the read characters.
        charCount += 1 # Increment character count.
        # If a semicolon has arrived then the FT991 has completed
        # sending output to the serial port so stop reading characters.
        # Also stop if max characters received. 
        if c == termchar:
            break
        if charCount > _SERIAL_READ_BUFFER_LENGTH:
            raise Exception('serial read buffer overflow')
    device.flushInput() # Flush serial buffer to prevent overflows.
    return answer           
## end def

def sendCommand(device, command):
    """
    Description: writes a string to the device.
    Parameters:  device - a serial object connected to the device port
                 command - string containing the FT991 command
    Returns:     nothing
    """
    device.write(command) # Send command string to FT991
    device.flushOutput() # Flush serial buffer to prevent overflows

# Iterate through all menu items, getting each setting
def readMenuSettings(device):
    """
    Description: prints out all menu settings.
    Parameters:  device - a serial object connected to the FT991
    Returns:     nothing
    """
    for inx in range(1,125):
        sCommand = 'EX%0.3d;' % inx
        sendCommand(device, sCommand)
        sAnswer = getAnswer(device, ';')
        print "%0.3d: %s" % (inx, sAnswer[5:])

# Iterate through all memory channels, getting settings
def readMemoryChannels(device):
    """
    Description: prints out all memory channels.
    Parameters:  device - a serial object connected to the FT991
    Returns:     nothing
    """
    for inx in range(1,118):
        sCommand = 'MT%0.3d;' % inx
        sendCommand(device, sCommand)
        sAnswer = getAnswer(device, ';')
        print "%0.3d: %s" % (inx, sAnswer)

def main():
    """
    Description: main routine starts command line interpreter.
    Parameters:  none
    Returns:     nothing
    """
    
    # Present an introductory splash when the program first starts up.
    splash = \
"""
Enter an FT991 command, e.g, "IF;";
or enter one of the following commands
    exit - terminates this program
    rmem - prints out memory channels
    rmenu - prints out all menu settings
"""
    print splash

    # Create a FT991 object for serial communication
    ft991 = serial.Serial(_SERIAL_PORT, _BAUD_RATE, timeout=_INTERFACE_TIMEOUT)
    time.sleep(.1) # give the connection a moment to settle

    while(True):
        sCommand = raw_input('>')
        # Process command string
        if sCommand == '': # no command - do nothing
            continue
        elif sCommand.upper() == 'EXIT': # end program
            break
        elif sCommand.upper() == 'RMEM': # display channel memory
            readMemoryChannels(ft991)
        elif sCommand.upper() == 'RMENU': # display menu settings
            readMenuSettings(ft991)
        else: # run a user command
            sendCommand(ft991, sCommand)
            sAnswer = getAnswer(ft991, ';');
            if sAnswer != '':
                print sAnswer
## end main

if __name__ == '__main__':
    main()
