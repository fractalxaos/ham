#!/usr/bin/python -u
# The -u option turns off block buffering of python output. This assures
# that output streams to stdout when output happens.
#
# Module: ft991.py
#
# Description:  This module contains tables for translating common transceiver
#               settings to FT991 CAT parameters.  Low level serial
#               communication functions are also handled by this module.  In
#               particular this module handles:
#                   1. Instantiating a serial connection object
#                   2. Sending character strings to the serial port
#                   3. Reading characters from the serial port
#                   4. Parsing and formatting of FT991 commands
#                   5. Translating radio operating parameters to CAT
#                      commands, i.e., CTCSS tones.  
#
# Copyright 2019 by Jeff Owrey, Intravisions.com
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
#    You should have received a copy of the GNU General Public Licensef
#    along with this program.  If not, see http://www.gnu.org/license.
#
# Revision History
#   * v10 24 Nov 2019 by J L Owrey; first release
#
# This script has been tested with the following
#
#     Python 2.7.15rc1 (default, Nov 12 2018, 14:31:15) 
#     [GCC 7.3.0] on linux2
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

import sys, serial, time

# General constant defines
_INTERFACE_TIMEOUT = 0.1 # seconds
_SERIAL_READ_TIMEOUT = 0.1 # seconds
_SERIAL_READ_BUFFER_LENGTH = 1024 # characters

# Define globals
verbose = False
debug = False
ptrDevice = None

# Define lookup tables for common transceiver settings.  Common settings
# such as modulation mode, repeater offset direction, DCS/CTCSS mode,
# CTCSS tone, and DCS code are translated to the repective FT991 parameter
# value.

# Modulation modes
dMode = { 'LSB':'1', 'USB':'2', 'CW':'3', 'FM':'4', 'AM':'5',
          'RTTY-LSB':'6', 'CW-R':'7', 'DATA-LSB':'8', 'RTTY-USB':'9',
          'DATA-FM':'A', 'FM-N':'B', 'DATA-USB':'C', 'AM-N':'D',
          'C4FM':'E' }

# Repeater shift direction
dShift = { 'OFF':'0', '+RPT':'1', '-RPT':'2' }

# Power settings
dPower = { 'LOW':5, 'MID':020, 'HIGH':50, 'MAX':100 }

# Repeater signaling modes
dEncode = { 'OFF':'0', 'ENC/DEC':'1', 'TONE ENC':'2',
            'DCS ENC/DEC':'4', 'DCS':'3' }

# CTCSS Tones
dTones = { '67.0 Hz':'000', '69.3 Hz':'001', '71.9 Hz':'002',
           '74.4 Hz':'003', '77.0 Hz':'004', '79.7 Hz':'005',
           '82.5 Hz':'006', '85.4 Hz':'007', '88.5 Hz':'008',
           '91.5 Hz':'009', '94.8 Hz':'010', '97.4 Hz':'011',
           '100.0 Hz':'012', '103.5 Hz':'013', '107.2 Hz':'014',
           '110.9 Hz':'015', '114.8 Hz':'016', '118.8 Hz':'017',
           '123.0 Hz':'018', '127.3 Hz':'019', '131.8 Hz':'020',
           '136.5 Hz':'021', '141.3 Hz':'022', '146.2 Hz':'023',
           '151.4 Hz':'024', '156.7 Hz':'025', '159.8 Hz':'026',
           '162.2 Hz':'027', '165.5 Hz':'028', '167.9 Hz':'029',
           '171.3 Hz':'030', '173.8 Hz':'031', '177.3 Hz':'032',
           '179.9 Hz':'033', '183.5 Hz':'034', '186.2 Hz':'035',
           '189.9 Hz':'036', '192.8 Hz':'037', '196.6 Hz':'038',
           '199.5 Hz':'039', '203.5 Hz':'040', '206.5 Hz':'041',
           '210.7 Hz':'042', '218.1 Hz':'043', '225.7 Hz':'044',
           '229.1 Hz':'045', '233.6 Hz':'046', '241.8 Hz':'047',
           '250.3 Hz':'048', '254.1 Hz':'049' } 

# DCS Tones
dDcs = { '23':'000', '25':'001', '26':'002', '31':'003', '32':'004',
         '36':'005', '43':'006', '47':'007', '51':'008', '53':'009',
         '54':'010', '65':'011', '71':'012', '72':'013', '73':'014',
         '74':'015', '114':'016', '115':'017', '116':'018', '122':'019',
         '125':'020', '131':'021', '132':'022', '134':'023', '143':'024',
         '145':'025', '152':'026', '155':'027', '156':'028', '162':'029',
         '165':'030', '172':'031', '174':'032', '205':'033', '212':'034',
         '223':'035', '225':'036', '226':'037', '243':'038', '244':'039',
         '245':'040', '246':'041', '251':'042', '252':'043', '255':'044',
         '261':'045', '263':'046', '265':'047', '266':'048', '271':'049',
         '274':'050', '306':'051', '311':'052', '315':'053', '325':'054',
         '331':'055', '332':'056', '343':'057', '346':'058', '351':'059',
         '356':'060', '364':'061', '365':'062', '371':'063', '411':'064',
         '412':'065', '413':'066', '423':'067', '431':'068', '432':'069',
         '445':'070', '446':'071', '452':'072', '454':'073', '455':'074',
         '462':'075', '464':'076', '465':'077', '466':'078', '503':'079',
         '506':'080', '516':'081', '523':'082', '526':'083', '532':'084',
         '546':'085', '565':'086', '606':'087', '612':'088', '624':'089',
         '627':'090', '631':'091', '632':'092', '654':'093', '662':'094',
         '664':'095', '703':'096', '712':'097', '723':'098', '731':'099',
         '732':'100', '734':'101', '743':'102', '754':'103' }

# Clarifier state
dRxClar = { 'OFF':'0', 'ON':'1' }
dTxClar = { 'OFF':'0', 'ON':'1' }

#############################################################################
# Define 'get' methods to encapsulate FT991 commands returning status info. #
#############################################################################

def getMemory(memloc):
    """
    Description: Get memory settings of a specific memory location.
    Parameters: memloc - an integer specifying memory location 
    Returns: a dictionary object containing the memory ettings
    """
    dMem = {}

    # Send the get memory settings string to the FT991.
    sCmd = 'MT%0.3d;' % (memloc)
    sResult = sendCommand(sCmd)
    if sResult == '?;':
        return None

    # Parse memory settings string returned by the FT991
    memloc = sResult[2:5]
    rxfreq = sResult[5:14]
    clarfreq = sResult[14:19]
    rxclar = sResult[19]
    txclar = sResult[20]
    mode = sResult[21]
    encode = sResult[23]
    shift = sResult[26]
    tag = sResult[28:40]

    # Store the memory settings in a dictionary object.
    dMem['memloc'] = str(int(memloc))
    dMem['rxfreq'] = str(float(rxfreq) / 10**6)
    dMem['clarfreq'] = str(int(clarfreq))
    dMem['rxclar'] = dRxClar.keys()[dRxClar.values().index(rxclar)]
    dMem['txclar'] = dTxClar.keys()[dTxClar.values().index(txclar)]
    dMem['mode'] = dMode.keys()[dMode.values().index(mode)]
    dMem['encode'] = dEncode.keys()[dEncode.values().index(encode)]
    dMem['shift'] = dShift.keys()[dShift.values().index(shift)]
    dMem['tag'] = tag.strip()

    return dMem
## end def

def getCTCSS():
    """
    Description: Get the CTCSS tone setting for the current memory location.
    Parameters: none
    Returns: string containing the CTCSS tone
    """
    # Get result CTCSS tone
    sResult = sendCommand('CN00;')
    tone = sResult[4:7]
    return dTones.keys()[dTones.values().index(tone)]
## end def

def getDCS():
    """
    Description: Get the DCS code setting for the current memory location.
    Parameters: none
    Returns: string containing the DCS code
    """
    # Get result of CN01 command
    sResult = sendCommand('CN01;')
    dcs = sResult[4:7]
    return dDcs.keys()[dDcs.values().index(dcs)]
## end def

def getRxClarifier():
    """
    Description:  Gets the state of the Rx clarifier.
    Parameters: none
    Returns: string containing the state of the clarifier
    """
    # An exception will automatically be raised if incorrect data is
    # supplied - most likely a "key not found" error.
    sCmd = 'RT;'
    sResult = sendCommand(sCmd)
    state = sResult[2]
    return dRxClar.keys()[dRxClar.values().index(state)]
## end def

def getTxClarifier():
    """
    Description:  Gets the state of the Tx clarifier.
    Parameters: none
    Returns: string containing the state of the clarifier
    """
    # An exception will automatically be raised if incorrect data is
    # supplied - most likely a "key not found" error.
    sCmd = 'XT;'
    sResult = sendCommand(sCmd)
    state = sResult[2]
    return dTxClar.keys()[dTxClar.values().index(state)]
## end def

#########################################################################
# Define 'set' functions to encapsulate the various FT991 CAT commands. #
#########################################################################

def setMemory(dMem):
    """
    Description: Sends a formatted MT command.
    Parameters: dMem - a dictionary objected with the following keys
                       defined:

                       memloc - the memory location to be written
                       rxfreq - receive frequency of VFO-A in MHz
                       clarfreq - clarifier frequency and direction
                       rxclar - receive clarifier state
                       txclar - transmit clarifier state
                       mode - the modulation mode
                       encode - the tone or DCS encoding mode
                       shift - the direction of the repeater shift
                       tag - a label for the memory location

    Returns: nothing
    """
    # Format the set memory with tag command (MT).
    sCmd = 'MT'

    # Validate and append memory location data.
    iLocation = int(dMem['memloc'])
    if iLocation < 1 or iLocation > 118:
        raise Exception('Memory location must be between 1 and ' \
                        '118, inclusive.')
    sCmd += '%0.3d' % iLocation

    # Validate and append the vfo-a frequency data.
    iRxfreq = int(float(dMem['rxfreq']) * 1E6) # vfo-a frequency in Hz
    if iRxfreq < 0.030E6 or iRxfreq > 450.0E6:
        raise Exception('VFO-A frequency must be between 30 kHz and ' \
                        '450 MHz, inclusive.')
    sCmd += '%0.9d' % iRxfreq

    # Validate and append the clarifier data.
    iClarfreq = int(dMem['clarfreq'])
    if abs(iClarfreq) > 9999:
        raise Exception('Clarifer frequency must be between -9999 Hz ' \
                        'and +9999 Hz, inclusive.')
    sCmd += '%+0.4d' % iClarfreq

    # The following commands will automatically raise an exception if
    # incorrect data is supplied.  The exception will be a dictionary
    # object "key not found" error.
    sCmd += dRxClar[dMem['rxclar']]
    sCmd += dTxClar[dMem['txclar']]
    sCmd += dMode[dMem['mode']]
    sCmd += '0'
    sCmd += dEncode[dMem['encode']]
    sCmd += '00'
    sCmd += dShift[dMem['shift']]
    sCmd += '0'
    sTag = dMem['tag']

    # Validate and append the memory tag data.
    if len(sTag) > 12:
        raise Exception('Memory tags must be twelve characters or less.')
    sCmd += '%-12s' % sTag
    sCmd += ';' # Terminate the completed command.

    # Send the completed command.
    sResult = sendCommand(sCmd)
    if sResult == '?;':
        raise Exception('setMemory error')
## end def

def setCTCSS(tone):
    """
    Description:  Sends a formatted CN command that sets the desired
                  CTCSS tone.
    Parameters:   tone - a string containing the CTCSS tone in Hz, e.g.,
                         '100 Hz'
    Returns: nothing
    """
    # An exception will automatically be raised if incorrect data is
    # supplied - most likely a "key not found" error.
    sCmd = 'CN00%s;' % dTones[tone]
    # Send the completed command.
    sResult = sendCommand(sCmd)
    if sResult == '?;':
        raise Exception('setCTCSS error')
## end def

def setDCS(code):
    """
    Description:  Sends a formatted CN command that sets the desired
                  DCS code.
    Parameters: code - a string containing the DCS code, e.g., '23'
    Returns: nothing
    """
    # An exception will automatically be raised if incorrect data is
    # supplied - most likely a "key not found" error.
    sCmd = 'CN01%s;' % dDcs[code]
    # Send the completed command.
    sResult = sendCommand(sCmd)
    if sResult == '?;':
        raise Exception('setDCS error')
## end def

def setPower(power):
    """
    Description:  Sends a PC command that sets the desired
                  RF transmit power level.
    Parameters:   power - Watts, an integer between 5 and 100
    Returns: nothing
    """
    power = int(power)
    # Validate power data and format command.
    if power < 5 or power > 100:
        raise Exception('Power must be between 0 and 100 watts, inclusive.')
    sCmd += 'PC%03.d;' % power
    # Send the completed command.
    sResult = sendCommand(sCmd)
    if sResult == '?;':
        raise Exception('setPower error')

## end def

def setRxClarifier(state='OFF'):
    """
    Description:  Sends a formatted RT command that turns the Rx clarifier
                  on or off.
    Parameters: state - string 'OFF' or 'ON'
    Returns: nothing
    """
    # An exception will automatically be raised if incorrect data is
    # supplied - most likely a "key not found" error.
    sCmd = 'RT%s;' % dRxClar[state]
    # Send the completed command.
    sResult = sendCommand(sCmd)
    if sResult == '?;':
        raise Exception('setRxClarifier error')
## end def

def setTxClarifier(state='OFF'):
    """
    Description:  Sends a formatted XT command that turns the Rx clarifier
                  on or off.
    Parameters: state - string 'OFF' or 'ON'
    Returns: nothing
    """
    # An exception will automatically be raised if incorrect data is
    # supplied - most likely a "key not found" error.
    sCmd = 'XT%s;' % dTxClar[state]
    # Send the completed command.
    sResult = sendCommand(sCmd)
    if sResult == '?;':
        raise Exception('setTxClarifier error')
## end def

def setMemoryLocation(iLocation):
    """
    Description:  Sends a formatted MC command that sets the current
                  memory location.
    Parameters: location - integer specifying memory location
    Returns: nothing
    """
    # Validate memory location data and send the command.
    if iLocation < 1 or iLocation > 118:
        raise Exception('Memory location must be an integer between 1 and ' \
                        '118, inclusive.')
    sCmd = 'MC%0.3d;' % iLocation
    # Send the completed command.
    sResult = sendCommand(sCmd)
    if sResult == '?;':
        raise Exception('setMemoryLocation error')
## end def

############################################################################
# Helper functions to assist in various tasks.                             #
############################################################################

def parseCsvData(sline):
    """
    Description:  stores each item in the comma delimited line in a single
                  dictionary object using a key appropriate for that item.
    Parameters: a string containing the comma delimited items to be parsed.
    Returns: a dictionary object containing the parsed line.
    """
    dChan = {} # define an empty dictionary object
    lchan = sline.split(',') # split the line at the commas
    # If the first line is a header line, ignore it.
    if not lchan[0].isdigit():
        return None
    # Store the parsed items with the appropriate key in the dictionary object.
    dChan['memloc'] = lchan[0]
    dChan['rxfreq'] = lchan[1]
    dChan['txfreq'] = lchan[2]
    dChan['offset'] = lchan[3]
    dChan['shift'] = lchan[4]
    dChan['mode'] = lchan[5]
    dChan['tag'] = lchan[6]
    dChan['encode'] = lchan[7]
    dChan['tone'] = lchan[8]
    dChan['dcs'] = lchan[9]
    dChan['clarfreq'] = lchan[10]
    dChan['rxclar'] = lchan[11]
    dChan['txclar'] = lchan[12]
    return dChan # return the dictionary object
## end def

def sendCommand(sCmd):
    """
    Description: Sends a formatted FT911 command to the communication
                 port connected to the FT991.  Prints to stdout the
                 answer from the FT991 (if any).
    Parameters: device - a pointer to the FT991 comm port
                sCmd - a string containing the formatted command
    Returns: nothing
    """
    # Debug mode in conjunction with verbose mode is for verifying
    # correct formatting of commands before they are actually sent
    # to the FT991.
    if verbose:
        print sCmd,
    # In debug mode do not actually send commands to the FT991.
    if debug:
        return ''

    # Send the formatted command to the FT991 and get an answer, if any.
    # If the command does not generate an answer, no characters will be
    # returned by the FT991, resulting in an empty string returned by
    # the receiveSerial function.
    sendSerial(sCmd)
    sResult  = receiveSerial();
    if verbose:
        print sResult
    return sResult
## end def

# Low level serial communications functions.

def begin(baud=9600):
    """
    Description: Initiates a serial connection the the FT991. Should
                 always be called before sending commands to or
                 receiving data from the FT991.  Only needs to be called
                 once.
    Parameters: none
    Returns: a pointer to the FT991 serial connection
    """
    global ptrDevice

    # Determine OS type and set device port accordingly.
    OS_type = sys.platform
    if 'WIN' in OS_type.upper():
        port = 'COM5'
    else:
        port = '/dev/ttyUSB0'

    # In debug mode do not actually send commands to the FT991.
    if debug:
        return

    # Create a FT991 object for serial communication
    try:
        ptrDevice = serial.Serial(port, baud,      
                                  timeout=_INTERFACE_TIMEOUT)
    except Exception, error:
        if str(error).find('could not open port') > -1:
            print 'Please be sure the usb cable is properly connected to\n' \
                  'your FT991 and to your computer, and that the FT991 is\n' \
                  'turned ON.  Then restart this program.'
        else:
            print 'Serial port error: %s\n' % error
        exit(1)         
    time.sleep(.1) # give the connection a moment to settle
    return ptrDevice
## end def

def receiveSerial(termchar=';'):
    """
    Description: Reads output one character at a time from the device
                 until a terminating character is received.  Returns a     
                 string containing the characters read from the serial
                 port.
    Parameters:  termchar - character terminating the answer string
    Returns: a string containing the received data
    """
    answer = '' # initialize answer string to empty string
    charCount = 0  # reset read character count to zero

    while True:
        startTime = time.time() # Start read character timer
        c =''
        while True:
            # Check for a character available in the serial read buffer.
            if ptrDevice.in_waiting:
                c = ptrDevice.read()
                break
            # Timeout if a character does not become available.
            if time.time() - startTime > _SERIAL_READ_TIMEOUT:
                break # Character waiting timer has timed out.
        # Return empty string if a character has not become available.
        if c == '':
            break;
        answer += c # Form a string from the received characters.
        charCount += 1 # Increment character count.
        # If a semicolon has arrived then the FT991 has completed
        # sending output to the serial port so stop reading characters.
        # Also stop if max characters received. 
        if c == termchar:
            break
        if charCount > _SERIAL_READ_BUFFER_LENGTH:
            raise Exception('serial read buffer overflow')
    ptrDevice.flushInput() # Flush serial buffer to prevent overflows.
    return answer           
## end def

def sendSerial(command):
    """
    Description: Writes a string to the device.
    Parameters: command - string containing the FT991 command
    Returns: nothing
    """
    # In debug we only want to see the output of the command formatter,
    # not actually send commands to the FT991.  Debug mode should be
    # used in conjunction with verbose mode.
    ptrDevice.write(command) # Send command string to FT991
    ptrDevice.flushOutput() # Flush serial buffer to prevent overflows
## end def

# Main routine only gets called when this module is run as a program rather
# than imported into another python module.  Code testing the functions in
# this module should be placed here.

def main():
    """
    Description: Place code for testing this module here.
    Parameters: none
    Returns: nothing
    """
    # Test this module.
    global verbose, debug

    verbose = True
    debug = False

    # Instantiate serial connection to FT991
    begin()
    # Set and receive a memory channel
    dMem = {'memloc': '98', 'rxfreq': '146.52', 'shift': 'OFF', \
            'mode': 'FM', 'encode': 'TONE ENC', 'tag': 'KA7JLO', \
            'clarfreq': '1234', 'rxclar': 'ON', 'txclar': 'ON' \
           }
    setMemory(dMem)
    setMemoryLocation(int(dMem['memloc']))
    setRxClarifier(dMem['rxclar'])
    setTxClarifier(dMem['txclar'])
    setCTCSS('127.3 Hz')
    setDCS('115')
    print
    getMemory(98)
    print
    # Set and receive a memory channel
    dMem = {'memloc': '99', 'rxfreq': '146.52', 'shift': 'OFF', \
            'mode': 'FM', 'encode': 'OFF', 'tag': 'KA7JLO', \
            'clarfreq': '0', 'rxclar': 'OFF', 'txclar': 'OFF' \
           }
    setMemory(dMem)
    setMemoryLocation(int(dMem['memloc']))
    setRxClarifier(dMem['rxclar'])
    setTxClarifier(dMem['txclar'])
    setCTCSS('141.3 Hz')
    setDCS('445')
    print
    getMemory(99)
    print

    # Test set commands
    #setMemoryLocation(2)
    # Test get commands
    #   commands...
    # Test CAT commands via direct pass-through
    # Commands that return data
    sendCommand('IF;')
    # Invalid command handling
    sendCommand('ZZZ;')
## end def

if __name__ == '__main__':
    main()
