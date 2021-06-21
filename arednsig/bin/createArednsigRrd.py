#!/usr/bin/python -u
## The -u option above turns off block buffering of python output. This assures
## that each error message gets individually printed to the log file.
#
# Module: createArednsigRrd.py
#
# Description: Creates a rrdtool database for use by the weather agent to
# store the data from the weather station.  The agent uses the data in the
# database to generate graphic charts for display in the weather station
# web page.
#
# Copyright 2020 Jeff Owrey
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
#   * v10 released 11 Jan 2020 by J L Owrey
#
import os
import time
import subprocess

    ### DEFINE FILE LOCATIONS ###

_USER = os.environ['USER']
# the file that stores the data
_RRD_FILE = "/home/%s/database/arednsigData.rrd" % _USER
_RRD_SIZE_IN_DAYS = 370 # days
_1YR_RRA_STEPS_PER_DAY = 96
_DATABASE_UPDATE_INTERVAL = 60

def createRrdFile():
    """Create the rrd file if it does not exist.
       Parameters: none
       Returns: True, if successful
    """

    if os.path.exists(_RRD_FILE):
        print "aredn node database already exists"
        return True

     ## Calculate database size
 
    heartBeat = 2 * _DATABASE_UPDATE_INTERVAL
    rra1yrNumPDP =  int(round(86400 / (_1YR_RRA_STEPS_PER_DAY * \
                    _DATABASE_UPDATE_INTERVAL)))
    rrd24hrNumRows = int(round(86400 / _DATABASE_UPDATE_INTERVAL))
    rrd1yearNumRows = _1YR_RRA_STEPS_PER_DAY * _RRD_SIZE_IN_DAYS
       
    strFmt = ("rrdtool create %s --start now-1day --step %s "
              "DS:S:GAUGE:%s:U:U DS:N:GAUGE:%s:U:U DS:SNR:GAUGE:%s:U:U "
              "DS:RX_MCS:GAUGE:%s:U:U DS:TX_MCS:GAUGE:%s:U:U "
              "DS:RX_RATE:GAUGE:%s:U:U DS:TX_RATE:GAUGE:%s:U:U "
              "RRA:LAST:0.5:1:%s RRA:LAST:0.5:%s:%s")

    strCmd = strFmt % (_RRD_FILE, _DATABASE_UPDATE_INTERVAL, \
                heartBeat, heartBeat, heartBeat, heartBeat,  \
                heartBeat,  heartBeat, heartBeat,            \
                rrd24hrNumRows, rra1yrNumPDP, rrd1yearNumRows)

    print "creating aredn node database...\n\n%s\n" % strCmd

    # Spawn a sub-shell and run the command
    try:
        subprocess.check_output(strCmd, stderr=subprocess.STDOUT, \
                                shell=True)
    except subprocess.CalledProcessError, exError:
        print "rrdtool create failed: %s" % (exError.output)
        return False
    return True
##end def

def main():
    createRrdFile()
## end def

if __name__ == '__main__':
    main()
        
