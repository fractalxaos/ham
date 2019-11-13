#!/usr/bin/python -u
# The -u option turns off block buffering of python output. This assures
# that output streams to stdout when output happens.
#
# Description:  This program reads a comma delimited spreadsheet file
#               containing common transceiver settings.  The settings
#               are stored in the transceivers memory.
#
# This script has been tested with the following
#
#     Python 2.7.15rc1 (default, Nov 12 2018, 14:31:15) 
#     [GCC 7.3.0] on linux2
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

# Import python library modules. The serial module should be included in
# recent linux distributions.  If not, it may need to be installed.
import sys, serial, time
# Import FT991 serial communication functions and command library.  This
# is a custom module that should be in the same folder as this script.
import ft991

# Define default memory settings file
_SETTINGS_FILE = './ft991mem.csv'

# Define global variables
settingsFile = _SETTINGS_FILE

def readSettingsFile(fileName):
    """
    Description: reads the comma delimited memory settings file and parses
                 each line of that file into a dictionary object which stores
                 the settings for that memory location.  Each dictionary
                 object in turn gets stored in a single list object.
    Parameters: name of memory settings file
    Returns: a list object
    """
    lChan = []
    fchs = open(fileName, 'r') # open the file for reading
    # read a line from the file
    for line in fchs:
        # remove non-printable characters
        rline = line.strip()
        # parse the comma delimited line and store in a dictionary object
        dChanData = parseData(rline)
        # store the parsed line in a list object
        if dChanData != None:
            lChan.append(dChanData)
    fchs.close()
    return lChan

def parseData(sline):
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
    dChan['chnum'] = lchan[0]
    dChan['rxfreq'] = lchan[1]
    dChan['txfreq'] = lchan[2]
    dChan['offset'] = lchan[3]
    dChan['shift'] = lchan[4]
    dChan['mode'] = lchan[5]
    dChan['tag'] = lchan[6]
    dChan['encode'] = lchan[7]
    dChan['tone'] = lchan[8]
    dChan['dcs'] = str(int(lchan[9]))
    return dChan # return the dictionary object


def sendCommand(device, sCmd):
    """
    Description:  sends a formatted FT911 command to the communication port
                  connected to the FT991.  Prints to stdout the answer from
                  the FT991 (if any).
    Parameters: device - a pointer to the FT991 comm port
                sCmd - a string containing the formatted command
    Returns: nothing
    """
    ft991.sendSerial(device, sCmd)
    sAnswer = ft991.receiveSerial(device);
    if sAnswer != '':
        print sAnswer

def getCLarguments():
    """Get command line arguments.  There are four possible arguments
          -v turns on verbose mode
          -d turns on debug mode
          -f name of comman delimited memory settings file
       Returns: nothing
    """
    #global ft991.verbose, ft991.debug, settingsFile
    global settingsFile

    index = 1
    while index < len(sys.argv):
        if sys.argv[index] == '-f':
            if len(sys.argv) < index + 2:
                print "-f option requires file name"
                exit(1);
            settingsFile = sys.argv[index + 1]
            index += 1
        elif sys.argv[index] == '-v':
            ft991.verbose = True
        elif sys.argv[index] == '-d':
            ft991.debug = True
        else:
            cmd_name = sys.argv[0].split('/')
            print "Usage: %s [-v] [-f file]\n" \
                  "  -f: settings file\n" \
                  "  -v: verbose mode\n" \
                  "  -d: debug mode" % cmd_name[-1]
            exit(-1)
        index += 1
##end def

def main():
    """
    Description:  Reads the settings file, creating a list object which
                  contains dictionary objects as its elements.  The dictionary
                  objects contain the settings for each memory location to be
                  programmed.
    Parameters: none
    Returns: nothing
    """

    # Get command line arguments, if any.  Otherwise use defaults.
    getCLarguments()

    # Create a FT991 object for serial communication.
    pft991 = ft991.begin()
    time.sleep(.1) # give the connection a moment to settle

    # Read and parse the settings file.
    dChan = readSettingsFile(settingsFile)
    # Get and send the commands to the FT991 for writing the memory locations.
    for item in dChan:
        if ft991.verbose:
            print '%s: ' % item['chnum'],

        # Format and send memory channel vfo and mode data.
        sendCommand(pft991, ft991.getMTcommand(item))
        # Format and send CTCSS tone for memory channel.
        sendCommand(pft991, ft991.getCTCSScommand(item))
        # Format and send DCS code for memory channel. 
        sendCommand(pft991, ft991.getDCScommand(item))

        if ft991.verbose:
            print
## end def

if __name__ == '__main__':
    main()
