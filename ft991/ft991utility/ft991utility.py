#!/usr/bin/python -u
# The -u option turns off block buffering of python output. This assures
# that output streams to stdout when output happens.
#
# Module: ft991utility.py
#
# Description:  A utility for backing up Yaesu FT991 memory and menu settings,
#               and also for restoring memory and menu settings from
#               a file.  Can be used both interactively or with command line
#               arguments. Before running this utility, be sure to copy
#               the file 'ft911.py' to the same folder as this utility.
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
#   * v10 23 Nov 2019 by J L Owrey; first release
#
# This script has been tested with the following
#
#     Python 2.7.15rc1 (default, Nov 12 2018, 14:31:15) 
#     [GCC 7.3.0] on linux2
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

import os, sys, serial, time
import ft991 # module should be in same directory as this utility

# Constant definitions

_DEFAULT_MENU_SETTINGS_FILE = 'ft991menu.cfg'
_DEFAULT_MEMORY_SETTINGS_FILE = 'ft991mem.csv'
_MAX_NUMBER_OF_MENU_ITEMS = 154
_MAX_NUMBER_OF_MEMORY_ITEMS = 118

# Global definitions

menuBackupFile = _DEFAULT_MENU_SETTINGS_FILE
memoryBackupFile = _DEFAULT_MEMORY_SETTINGS_FILE
commandLineOption = ''

# Command processing functions

def doUserCommand():
    """
    Description: Provides an interactive user interface where the user can
                 enter simple text commands at a command line prompt.  The
                 commands that a user can enter are listed in a menu splash
                 that the user can display anytime with the 'm' command.
                 Also this function processes commands provided as command
                 line options.  In the case of a command line option this
                 function operates non-interactively.
    Parameters: none
    Returns: nothing
    """
    # When command line arguments have not been provided,
    # use interactive mode and give the user a prompt.
    if commandLineOption == '':
        cmd = raw_input('>').strip()
    # If command line arguments have been provided, then
    # execute the command non-interactively.
    else:
        cmd = commandLineOption

    # Process the user command.   
    if cmd == '':
        return
    elif cmd == 'm':
        printMenuSplash()
    elif cmd == 'bu':
        backupMenuSettings()
    elif cmd == 'ru':
        restoreMenuSettings()
    elif cmd == 'bm':
        backupMemorySettings()
    elif cmd == 'rm':
        restoreMemorySettings()
    elif cmd == 'p':
        passThroughMode()
    elif cmd == 'v':
        toggleVerboseMode()
    elif cmd == 'x':
        exit(0)
    else:
        print "invalid command"
## end def

def backupMemorySettings():
    """
    Description: Backs up all memory settings to a file.  The user has the
                 option of providing a file name or accepting a default
                 file name.
    Parameters: none
    Returns: nothing
    """
    # Prompt the user for a file name in which to store
    # backed up memory settings.
    fileName = getFileName(memoryBackupFile)
    # Read the memory settings from the FT991...
    print 'Backing up memory settings...'
    settings = readMemorySettings()
    # and write them to the file.
    writeToFile(settings, fileName)
    print 'Memory settings backed up to \'%s\'' % fileName
## end def

def restoreMemorySettings():
    """
    Description: Restores all memory settings from a file.  The user has the
                 option of providing a file name or accepting a default
                 file name.
    Parameters: none
    Returns: nothing
    """
    # Prompt the user for a file name from which to retrieve backed up
    # memory settings.  Also make sure the file exists.
    fileName = getFileName(memoryBackupFile)
    if not os.path.isfile(fileName):
        print 'File not found.\n' \
              'Please enter a valid file name.  Be sure to correctly ' \
              'enter\nthe full path name or relative path name of the file.'
        return
    # Read the memory settings from the file...
    print 'Restoring memory settings...'
    settings = readFromFile(fileName)
    # and write them to the FT991.
    writeMemorySettings(settings)
    print 'Memory settings restored from \'%s\'' % fileName
## end def

def backupMenuSettings():
    """
    Description: Backs up all menu settings to a file.  The user has the
                 option of providing a file name or accepting a default
                 file name.
    Parameters: none
    Returns: nothing
    """
    # Prompt the user for a file name in which to store
    # backed up menu settings.
    fileName = getFileName(menuBackupFile)
    # Read the menu settings from the FT991...
    print 'Backing up menu settings...'
    settings = readMenuSettings()
    # and write them to the file.
    writeToFile(settings, fileName)
    print 'Menu settings backed up to \'%s\'' % fileName
## end def

def restoreMenuSettings():
    """
    Description: Restores all menu settings from a file.  The user has the
                 option of providing a file name or accepting a default
                 file name.
    Parameters: none
    Returns: nothing
    """
    # Prompt the user for a file name from which to retrieve backed up
    # menu settings.  Also make sure the file exists.
    fileName = getFileName(menuBackupFile)
    if not os.path.isfile(fileName):
        print 'File not found.\n' \
              'Please enter a valid file name.  Be sure to correctly ' \
              'enter\nthe full path name or relative path name of the file.'
        return
    # Read the menu settings from the file...
    print 'Restoring menu settings...'
    settings = readFromFile(fileName)
    # and write them to the FT991.
    writeMenuSettings(settings)
    print 'Menu settings restored from \'%s\'' % fileName
## end def

def passThroughMode():
    """
    Description: An interactive mode whereby the user an enter FT991 CAT
                 commands directly on the command line.  This mode greatly
                 facilitates development and debugging.
    Parameters: none
    Returns: nothing
    """
    print 'Entering passthrough mode. Type \'exit\' to exit mode.'
    while(True):
        # Prompt the user to enter an FT991 CAT command, and
        # process the  command string.
        sCommand = raw_input('CAT# ').upper()
        if sCommand == 'EXIT': # exit this utility
            break
        # If the user fails to end a CAT command with a semi-colon,
        # then provide one.
        elif sCommand[-1:] != ';':
            sCommand += ';'

        if sCommand == '': # no command - do nothing
            continue
        else: # run a user command
            ft991.sendSerial(sCommand)
            sResult = ft991.receiveSerial();
            if sResult != '':
                print sResult
## end def

def toggleVerboseMode():
    """
    Description: Toggles the verbose mode on or off, depending on the
                 previous state.  Verbose mode causes CAT commands to be
                 echoed to STDOUT as they are sent to the FT991.  If a
                 CAT command returns a string, that is also echoed. 
    Parameters: none
    Returns: nothing
    """
    if ft991.verbose:
        ft991.verbose = False
        print 'Verbose is OFF'
    else:
        ft991.verbose = True
        print 'Verbose is ON'  
## end def

def getFileName(defaultFile):
    """
    Description: Prompts the user for a file name.
    Parameters: defaultFile - file name to use if the user does not
                              provide a file name
    Returns: the user provided file name if provided, or the default
             file name, otherwise.
    """
    # If a command backup or restore argument provided, then do not
    # query the user for a file name.  A file name may be provided
    # as an option on the command line.
    if commandLineOption != '':
        return defaultFile
    # Otherwise query the user for a file name
    fileName = raw_input('Enter file name or <CR> for default: ')
    if fileName == '':
        return defaultFile
    else:
        return fileName
## end def

def readMemorySettings():
    """
    Description: Reads all defined memory settings from the FT991.  The
                 settings are reformatted into a readable, comma-delimited
                 (csv) file, which can be viewed and modified with a
                 spreadsheet application such as LibreOffice Calc.
    Parameters: none
    Returns: a list object containing memory location settings. Each item
             in the list represents a row, in comma-delimited form, that
             specifies the settings for a single memory location. The first
             item in the list are the column headers for remaining rows
             contained in the list.
    """
    # Define the column headers as the first item in the list.
    lSettings = [ 'Memory Ch,Rx Frequency,Tx Frequency,Offset,' \
                        'Repeater Shift,Mode,Tag,Encoding,Tone,DCS,' \
                        'Clarifier, RxClar, TxClar' ]

    for iLocation in range(1, _MAX_NUMBER_OF_MEMORY_ITEMS):

        # For each memory location get the memory contents.  Note that
        # several CAT commands are required to get the entire contents
        # of a memory location.  Specifically, additional commands are
        # required to get DCS code and CTCSS tone.
        dMem = ft991.getMemory(iLocation)
        # If a memory location is empty (has not been programmed or has
        # been erased), do not created a list entry for that location.
        if dMem == None:
            continue
        # Set current memory location to the channel being set.
        sResult = ft991.setMemoryLocation(iLocation)
        # Get DCS and CTCSS.
        tone = ft991.getCTCSS()
        dcs = ft991.getDCS()
        # getMemory, above, stores data in a dictionary object.  Format
        # the data in this object, as well as, the DCS code and CTCSS
        # tone into a comma-delimited string.
        sCsvFormat = '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,' % \
               ( dMem['memloc'], dMem['rxfreq'], '', '', \
                 dMem['shift'], dMem['mode'], dMem['tag'], dMem['encode'], \
                 tone, dcs, dMem['clarfreq'], dMem['rxclar'], \
                 dMem['txclar'] )
        # Add the comma-delimited string to the list object.
        lSettings.append(sCsvFormat)
    return lSettings
# end def

def writeMemorySettings(lSettings):
    """
    Description: Writes the supplied memory settings to the FT991.
    Parameters: lSettings - a list object containing the memory
                                  settings in comma delimited format
    Returns: nothing
    """
    for item in lSettings:
        # Parse the comma-delimited line and store in a dictionary object.
        dItem = ft991.parseCsvData(item)
        # The first item in the memory settings list are the column headers;
        # so ignore this item.  (parseData returns None for this item.)
        if dItem == None:
            continue
        try:
            # Set the parameters for the memory location.
            ft991.setMemory(dItem)
            # Set current channel to memory location being set.
            ft991.setMemoryLocation(int(dItem['memloc']))
            # Set CTCSS tone for memory channel.
            ft991.setCTCSS(dItem['tone'])
            # Set DCS code for memory channel. 
            ft991.setDCS(dItem['dcs'])
            # Set clarifier mode.  Note that
            # while the 'MW' and 'MT' commands can be used to turn the Rx
            # and Tx clarifiers on, the clarifier states can only be turned
            # off by sending the 'RT0' and 'XT0' commands.  This situation
            # is probably due to a bug in the CAT interface.
            ft991.setRxClarifier(dItem['rxclar'])
            ft991.setTxClarifier(dItem['txclar'])            
        except Exception, e:
            print 'Memory settings restore operation failed. Most likely\n' \
                  'this is due to the backup settings file corrupted or\n' \
                  'incorrectly formatted. Look for the following error: \n'
            print e
            exit(1)
## end def

def readMenuSettings():
    """
    Description: Reads all menu settings from the FT991.
    Parameters: none
    Returns: a list object containing all the menu settings
    """
    lSettings = []
    # Iterate through all menu items, getting each setting and storing
    # the setting in a file.
    for inx in range(1, _MAX_NUMBER_OF_MENU_ITEMS):
        # Format the read menu item CAT command.
        sCommand = 'EX%0.3d;' % inx
        # Send the command to the FT991.
        sResult = ft991.sendCommand(sCommand)
        # Add the menu setting to a list object.
        lSettings.append(sResult)
    return lSettings
## end def

def writeMenuSettings(lSettings):
    """
    Description: Writes supplied menu settings to the FT991.
    Parameters: lSettings - a list object containing menu settings
    Returns: nothing
    """
    for item in lSettings:

        # Do not write read-only menu settings as this results
        # in the FT-991 returning an error.  The only read-only
        # setting is the "Radio ID" setting.
        if item.find('EX087') > -1:
            continue;
        # Send the pre-formatted menu setting to the FT991.
        sResult = ft991.sendCommand(item)
        if sResult.find('?;') > -1:
            print 'error restoring menu setting: %s' % item
            exit(1)
## end def

def writeToFile(lSettings, fileName):
    """
    Description: Writes supplied settings to the specified file.
    Parameters: lSettings - a list object containing the settings
                 fileName - the name of the output file
    Returns: nothing
    """
    fout = open(fileName, 'w')
    for item in lSettings:
        fout.write('%s\n' % item)
    fout.close()
## end def

def readFromFile(fileName):
    """
    Description: Reads settings from the specified file.
    Parameters:  fileName - the name of the input file
    Returns: a list object containing the settings
    """
    lSettings = []

    fin = open(fileName, 'r')
    for line in fin:
        item = line.strip() # remove new line characters
        lSettings.append(item)
    fin.close()
    return lSettings
## end def

def setIOFile(option, commandLineFile):
    """
    Description: Provides a connector between the command line and the
                 interactive interface.  Commands included as arguments
                 on the command line determine default file names, as
                 well as the command executed by doUserCommand above. 
    Parameters: option - the command supplied by the command line
                         argument interpreter getCLarguments.
                commandLineFile - the name of the file supplied by the -f
                         command line argument (if supplied). 
    Returns: nothing
    """
    global menuBackupFile, memoryBackupFile, commandLineOption

    commandLineOption = option
    if commandLineFile == '':
        return
    if (option == 'bu' or option == 'ru'):
        menuBackupFile = commandLineFile # set menu backup file name
    elif (option == 'bm' or option == 'rm'):
        memoryBackupFile = commandLineFile # set memory backup file name
## end def

def printMenuSplash():
    """
    Description: Prints an menu of available commands for use in
                 interactive mode.
    Parameters:  none
    Returns: nothing
    """
    splash = \
"""
Enter a command from the list below:
m - show this menu
bm - backup memory to file
rm - restore memory from file
bu - backup menu to file
ru - restore menu from file
p - enter pass through mode
v - toggle verbose mode
x - exit this program
"""
    print splash
## end def

def getCLarguments():
    """ Description: Gets command line arguments and configures this program
                     to run accordingly.  See the variable 'usage', below,
                     for possible arguments that may be used on the command
                     line.
        Parameters: none
        Returns: nothing
    """
    index = 1
    fileName = ''
    backupOption = ''

    # Define a splash to help the user enter command line arguments.
    usage =  "Usage: %s [-v] [OPTION] [-f file]\n"  \
             "  -b: backup memory\n"                \
             "  -r: restore memory\n"               \
             "  -m: backup menu\n"                  \
             "  -s: restore menu\n"                 \
             "  -f: backup/restore file name\n"     \
             "  -v: verbose mode\n"                 \
             % sys.argv[0].split('/')[-1]

    # Process all command line arguments until done.  Note that the last
    # dash b, m, r, or s argument encounterd on the command line will be
    # the one actually execute; any previous instances will be ignored.
    while index < len(sys.argv):
        if sys.argv[index] == '-f': # Backup file provided.
            # Get the backup file name.
            if len(sys.argv) < index + 2:
                print "-f option requires file name"
                exit(1);
            fileName = sys.argv[index + 1]
            index += 1
        elif sys.argv[index] == '-b': # backup memory
            backupOption = 'bm' 
        elif sys.argv[index] == '-r': # restore memory
            backupOption = 'rm'
        elif sys.argv[index] == '-m': # backup menu
            backupOption = 'bu'
        elif sys.argv[index] == '-s': # restore menu
            backupOption = 'ru'
        elif sys.argv[index] == '-v': # set verbose mode 'ON'
            ft991.verbose = True
        elif sys.argv[index] == '-d': # set debug mode 'ON'
            ft991.debug = True
        else:
            print usage
            exit(-1)
        index += 1
    ## end while

    # Set backup file name and backup command to execute.
    setIOFile(backupOption, fileName)
##end def

def main():
    """
    Description: Opens a com port connection to the FT991. Processes any
                 supplied command line options.  If no command line options
                 provides, then enters interactive mode.
    Parameters: none
    Returns: nothing
    """
    getCLarguments() # get command line options
    
    ft991.begin() # open com port session to FT991

    # Process command line options (if any).
    if commandLineOption != '':
       doUserCommand()
       return

    # Else enter user interactive mode.
    printMenuSplash()
    while(1):
        doUserCommand()
## end def

if __name__ == '__main__':
    main()
