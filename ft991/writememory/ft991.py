#!/usr/bin/python -u
# The -u option turns off block buffering of python output. This assures
# that output streams to stdout when output happens.
#
# Description:  This module contains tables for tranlating common transceiver
#               settings to FT991 CAT parameters.  Low level serial
#               communication functions are handled by this module.  In
#               particular this module handles:
#                   1. Setting a serial connection object
#                   2. Sending character strings to the serial port
#                   3. Reading characters from the serial port
#                   4. Formatting of FT991 commands
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

verbose = False
debug = False

# Define lookup tables for common transceiver settings.  Common settings
# such as modulation mode, repeater offset direction, DCS/CTCSS mode,
# CTCSS tone, and DCS code are translated to the repective FT991 parameter
# value.

dMode = {'LSB':'1', 'USB':'2', 'CW':'3', 'FM':'4', 'AM':'5', 'RTTY-LSB':'6',
         'CW-R':'7', 'DATA-LSB':'8', 'RTTY-USB':'9', 'DATA-FM':'A',
         'FM-N':'B', 'DATA-USB':'C', 'AM-N':'D', 'C4FM':'E'}

dShift = {'OFF':'0', '+RPT':'1', '-RPT':'2'}

dPower = { 'LOW':'005', 'MID':'020', 'HIGH':'050' }

dEncode = {'OFF':'0', 'ENC/DEC':'1', 'TONE ENC':'2', 'DCS ENC/DEC':'4',
          'DCS':'3'}

dTones = {'67.0 Hz':'000', '69.3 Hz':'001', '71.9 Hz':'002', '74.4 Hz':'003', 
       '77.0 Hz':'004', '79.7 Hz':'005', '82.5 Hz':'006', '85.4 Hz':'007',
       '88.5 Hz':'008', '91.5 Hz':'009', '94.8 Hz':'010', '97.4 Hz':'011',
       '100.0 Hz':'012', '103.5 Hz':'013', '107.2 Hz':'014', '110.9 Hz':'015',
       '114.8 Hz':'016', '118.8 Hz':'017', '123.0 Hz':'018', '127.3 Hz':'019',
       '131.8 Hz':'020', '136.5 Hz':'021', '141.3 Hz':'022', '146.2 Hz':'023',
       '151.4 Hz':'024', '156.7 Hz':'025', '159.8 Hz':'026', '162.2 Hz':'027',
       '165.5 Hz':'028', '167.9 Hz':'029', '171.3 Hz':'030', '173.8 Hz':'031',
       '177.3 Hz':'032', '179.9 Hz':'033', '183.5 Hz':'034', '186.2 Hz':'035',
       '189.9 Hz':'036', '192.8 Hz':'037', '196.6 Hz':'038', '199.5 Hz':'039',
       '203.5 Hz':'040', '206.5 Hz':'041', '210.7 Hz':'042', '218.1 Hz':'043',
       '225.7 Hz':'044', '229.1 Hz':'045', '233.6 Hz':'046', '241.8 Hz':'047',
       '250.3 Hz':'048', '254.1 Hz':'049'} 

dDcs = {'23':'000', '25':'001', '26':'002', '31':'003', '32':'004',
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
        '732':'100', '734':'101', '743':'102', '754':'103'}

# Define functions for implementing the various FT991 CAT commands

def getMTcommand(dChan):
    """
    Description: returns a formatted MT command to the calling function.
    Parameters: dChan - a dictionary objected with the following keys defined
                    chnum - the memory location to be written
                    rxfreq - the receive frequency of VFO-A in MHz
                    mode - the modulation mode
                    encode - the tone or DCS encoding mode
                    shift - the direction of the repeater shift
                    tag - a label for the memory location
    Returns: a string containing the formatted command
    """
    sCmd = 'MT'
    sCmd += '%0.3d' % int(dChan['chnum'])
    sCmd += '%d' % int(float(dChan['rxfreq']) * 1E6)
    sCmd += '+000000'
    sCmd += dMode[dChan['mode']]
    sCmd += '0'
    sCmd += dEncode[dChan['encode']]
    sCmd += '00'
    sCmd += dShift[dChan['shift']]
    sCmd += '0'
    sCmd += '%-12s' % dChan['tag']
    sCmd += ';'
    if verbose:
        print sCmd,
    return sCmd
 
def getCTCSScommand(dChan):
    """
    Description:  returns a formatted CN command that sets the desired
                  CTCSS tone.
    Parameters:  dChan - a dictionary object with the following key defined
                     tone - the CTCSS tone in Hz, e.g.,
                            dChan = {'tone':'100 Hz'}
    Returns: a string containing the formatted command
    """
    sCmd = 'CN0'
    sCmd += '0%s;' % dTones[dChan['tone']]
    if verbose:
        print sCmd,
    return sCmd

def getDCScommand(dChan):
    """
    Description:  returns a formatted CN command that sets the desired
                  DCS code.
    Parameters:  dChan - a dictionary object with the following key defined
                     dcs - the DCS code, e.g., dChan = {'dcs':'23'}
    Returns: a string containing the formatted command
    """
    sCmd = 'CN0'
    sCmd += '1%s;' % dDcs[dChan['dcs']]
    if verbose:
        print sCmd,
    return sCmd

def getPCcommand(dChan):
    """
    Description:  returns a formatted PC command that sets the desired
                  RF transmit power level.
    Parameters:  dChan - a dictionary object with the following key defined
                     power - the power level in Watts
                            e.g., dChan = {'power':'020'}
    Returns: a string containing the formatted command
    """
    sCmd = 'PC'
    sCmd += '%s;' % dPower[dChan['power']] 
    if verbose:
        print sCmd,
    return sCmd

def receiveSerial(device, termchar=';'):
    """
    Description: reads output one character at a time from the device
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
    device.flushInput() # Flush serial buffer to prevent overflows.
    return answer           
## end def

def sendSerial(device, command):
    """
    Description: writes a string to the device.
    Parameters:  device - a serial object connected to the device port
                 command - string containing the FT991 command
    Returns:     nothing
    """
    # In debug we only want to see the output of the command formatter,
    # not actually send commands to the FT991.  Debug mode should be
    # used in conjunction with verbose mode.
    if not debug: 
        device.write(command) # Send command string to FT991
        device.flushOutput() # Flush serial buffer to prevent overflows

def begin():
    """
    Description: initiates a serial connection the the FT991. Should always
                 be called before sending commands to or receiving data
                 from the FT991.  Only needs to be called once.
    Parameters: none
    Returns: a pointer to the FT991 serial connection
    """    # Create a FT991 object for serial communication
    pDevice = serial.Serial(_SERIAL_PORT, _BAUD_RATE,      
                            timeout=_INTERFACE_TIMEOUT)
    time.sleep(.1) # give the connection a moment to settle
    return pDevice


def main():
    """
    Description: functions and function calls that test the functions
                 in this module should be placed here.
    Parameters: none
    Returns: nothing
    """    # Test this module.
    verbose = True
    ft991 = begin()
    sendSerial(ft991,'if;')
    answer= receiveSerial(ft991)
    print answer
## end def

if __name__ == '__main__':
    main()
