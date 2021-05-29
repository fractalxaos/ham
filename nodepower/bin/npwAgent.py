#!/usr/bin/python2 -u
# The -u option above turns off block buffering of python output. This 
# assures that each error message gets individually printed to the log file.
#
# Module: nodepowerAgent.py
#
# Description: This module acts as an agent between the mesh network and
# node power and enviromental sensors.  The agent periodically polls the
# sensors and processes the data returned from the sensors, including
#     - conversion of data items
#     - update a round robin (rrdtool) database with the sensor data
#     - periodically generate graphic charts for display in html documents
#     - write the processed node status to a JSON file for use by html
#       documents
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

# Import required python libraries.
import os
import sys
import signal
import subprocess
import multiprocessing
import time

# Import sensor libraries.
import ina260 # power sensor
import tmp102 # temperature sensor

    ### SENSOR BUS ADDRESSES ###

# Set bus addresses of sensors
_PWR_SENSOR_ADDR = 0X40
_BAT_TMP_SENSOR_ADDR = 0x48
_AMB_TMP_SENSOR_ADDR = 0x4B
# Set bus selector
_BUS_SEL = 1

    ### FILE AND FOLDER LOCATIONS ###

_USER = os.environ['USER']
# folder for containing dynamic data objects
_DOCROOT_PATH = "/home/%s/public_html/power/" % _USER
# folder for charts and output data file
_CHARTS_DIRECTORY = _DOCROOT_PATH + "dynamic/"
# location of data output file
_OUTPUT_DATA_FILE = _DOCROOT_PATH + "dynamic/powerData.js"
# database that stores node data
_RRD_FILE = "/home/%s/database/powerData.rrd" % _USER

    ### GLOBAL CONSTANTS ###

# rrdtool database update interval in seconds
_DATABASE_UPDATE_INTERVAL = 30
# sensor data request interval in seconds
_DEFAULT_DATA_REQUEST_INTERVAL = 2
# chart update interval in seconds
_CHART_UPDATE_INTERVAL = 600
# standard chart width in pixels
_CHART_WIDTH = 600
# standard chart height in pixels
_CHART_HEIGHT = 150

   ### GLOBAL VARIABLES ###

# turn on or off of verbose debugging information
debugOption = False
verboseDebug = False

# frequency of data requests to sensors
dataRequestInterval = _DEFAULT_DATA_REQUEST_INTERVAL
# chart update interval
chartUpdateInterval = _CHART_UPDATE_INTERVAL
# last node request time
lastDataPointTime = -1

# Define each sensor.  This also initialzes each sensor.
pwr = ina260.ina260(_PWR_SENSOR_ADDR, _BUS_SEL)
btmp = tmp102.tmp102(_BAT_TMP_SENSOR_ADDR, _BUS_SEL)
atmp = tmp102.tmp102(_AMB_TMP_SENSOR_ADDR, _BUS_SEL)

  ###  PRIVATE METHODS  ###

def getTimeStamp():
    """
    Set the error message time stamp to the local system time.
    Parameters: none
    Returns: string containing the time stamp
    """
    return time.strftime( "%m/%d/%Y %T", time.localtime() )
##end def

def getEpochSeconds(sTime):
    """Convert the time stamp supplied in the weather data string
       to seconds since 1/1/1970 00:00:00.
       Parameters: 
           sTime - the time stamp to be converted must be formatted
                   as %m/%d/%Y %H:%M:%S
       Returns: epoch seconds
    """
    try:
        t_sTime = time.strptime(sTime, '%m/%d/%Y %H:%M:%S')
    except Exception, exError:
        print '%s getEpochSeconds: %s' % (getTimeStamp(), exError)
        return None
    tSeconds = int(time.mktime(t_sTime))
    return tSeconds
##end def

def terminateAgentProcess(signal, frame):
    """Send a message to log when the agent process gets killed
       by the operating system.  Inform downstream clients
       by removing input and output data files.
       Parameters:
           signal, frame - dummy parameters
       Returns: nothing
    """
    # Inform downstream clients by removing output data file.
    if os.path.exists(_OUTPUT_DATA_FILE):
       os.remove(_OUTPUT_DATA_FILE)
    print '%s terminating npw agent process' % \
              (getTimeStamp())
    sys.exit(0)
##end def

  ###  PUBLIC METHODS  ###

def getSensorData(dData):
    """Poll sensors for data.
       Parameters: none
       Returns: a string containing the node signal data if successful,
                or None if not successful
    """
    try:
        dData["time"] = getTimeStamp()
        dData["current"] = pwr.getCurrent()
        dData["voltage"] = pwr.getVoltage()
        dData["power"] = pwr.getPower()
        dData["battemp"] = btmp.getTempC()
        dData["ambtemp"] = atmp.getTempC()
     
    except Exception, exError:
        print "%s sensor error: %s" % (getTimeStamp(), exError)
        return False

    return True
##end def

def updateDatabase(dData):
    """
    Update the rrdtool database by executing an rrdtool system command.
    Format the command using the data extracted from the sensors.
    Parameters: dData - dictionary object containing data items to be
                        written to the rr database file
    Returns: True if successful, False otherwise
    """
 
    epochTime = getEpochSeconds(dData['time'])

    # Format the rrdtool update command.
    strFmt = "rrdtool update %s %s:%s:%s:%s:%s:%s"
    strCmd = strFmt % (_RRD_FILE, epochTime, dData['current'], \
             dData['voltage'], dData['power'], dData['battemp'], \
             dData['ambtemp'])

    if debugOption:
        print "%s" % strCmd # DEBUG

    # Run the command as a subprocess.
    try:
        subprocess.check_output(strCmd, shell=True,  \
                             stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError, exError:
        print "%s: rrdtool update failed: %s" % \
                    (getTimeStamp(), exError.output)
        return False

    return True
##end def

def writeOutputDataFile(dData):
    """Write node data items to the output data file, formatted as 
       a Javascript file.  This file may then be accessed and used by
       by downstream clients, for instance, in HTML documents.
       Parameters:
           sData - a string object containing the data to be written
                   to the output data file
       Returns: True if successful, False otherwise
    """
    # Write a JSON formatted file for use by html clients.  The following
    # data items are sent to the client file.
    #    * The last database update date and time
    #    * The data request interval
    #    * The sensor values

    # Create a JSON formatted string from the sensor data.
    sData = "[{\"period\":\"%s\", " % \
           (chartUpdateInterval)
    for key in dData:
        sData += '\"%s\":\"%s\", ' % (key, dData[key])
    sData = sData[:-2] + '}]\n'

    # Write the JSON formatted data to the output data file.
    try:
        fc = open(_OUTPUT_DATA_FILE, "w")
        fc.write(sData)
        fc.close()
    except Exception, exError:
        print "%s write output file failed: %s" % \
              (getTimeStamp(), exError)
        return False

    if verboseDebug:
        print sData[:-1]
    if debugOption:
        print "writing output data file: %d bytes" % len(sData)

    return True
## end def

def createGraph(fileName, dataItem, gLabel, gTitle, gStart,
                lower, upper, addTrend, autoScale):
    """Uses rrdtool to create a graph of specified node data item.
       Parameters:
           fileName - name of file containing the graph
           dataItem - data item to be graphed
           gLabel - string containing a graph label for the data item
           gTitle - string containing a title for the graph
           gStart - beginning time of the graphed data
           lower - lower bound for graph ordinate #NOT USED
           upper - upper bound for graph ordinate #NOT USED
           addTrend - 0, show only graph data
                      1, show only a trend line
                      2, show a trend line and the graph data
           autoScale - if True, then use vertical axis auto scaling
               (lower and upper parameters are ignored), otherwise use
               lower and upper parameters to set vertical axis scale
       Returns: True if successful, False otherwise
    """
    gPath = _CHARTS_DIRECTORY + fileName + ".png"
    trendWindow = { 'end-1day': 7200,
                    'end-4weeks': 172800,
                    'end-12months': 604800 }
 
    # Format the rrdtool graph command.

    # Set chart start time, height, and width.
    strCmd = "rrdtool graph %s -a PNG -s %s -e now -w %s -h %s " \
             % (gPath, gStart, _CHART_WIDTH, _CHART_HEIGHT)
   
    # Set the range and scaling of the chart y-axis.
    if lower < upper:
        strCmd  +=  "-l %s -u %s -r " % (lower, upper)
    elif autoScale:
        strCmd += "-A "
    strCmd += "-Y "

    # Set the chart ordinate label and chart title. 
    strCmd += "-v %s -t %s " % (gLabel, gTitle)
 
    # Show the data, or a moving average trend line over
    # the data, or both.
    strCmd += "DEF:dSeries=%s:%s:LAST " % (_RRD_FILE, dataItem)
    if addTrend == 0:
        strCmd += "LINE1:dSeries#0400ff "
    elif addTrend == 1:
        strCmd += "CDEF:smoothed=dSeries,%s,TREND LINE3:smoothed#ff0000 " \
                  % trendWindow[gStart]
    elif addTrend == 2:
        strCmd += "LINE1:dSeries#0400ff "
        strCmd += "CDEF:smoothed=dSeries,%s,TREND LINE3:smoothed#ff0000 " \
                  % trendWindow[gStart]
     
    if verboseDebug:
        print "%s" % strCmd # DEBUG
    
    # Run the formatted rrdtool command as a subprocess.
    try:
        result = subprocess.check_output(strCmd, \
                     stderr=subprocess.STDOUT,   \
                     shell=True)
    except subprocess.CalledProcessError, exError:
        print "rrdtool graph failed: %s" % (exError.output)
        return False

    if debugOption:
        print "rrdtool graph: %s\n" % result,
    return True

##end def

def generateGraphs():
    """Generate graphs for display in html documents.
       Parameters: none
       Returns: nothing
    """
    autoScale = False

    # 24 hour stock charts

    createGraph('24hr_current', 'CUR', 'mA', 
                'Current\ -\ Last\ 24\ Hours', 'end-1day', 0, 0, 2, autoScale)
    createGraph('24hr_voltage', 'VOLT', 'V', 
                'Voltage\ -\ Last\ 24\ Hours', 'end-1day', 0, 0, 2, autoScale)
    createGraph('24hr_power', 'PWR', 'mW', 
                'Power\ -\ Last\ 24\ Hours', 'end-1day', 0, 0, 2, autoScale)
    createGraph('24hr_battemp', 'BTMP', 'deg\ C', 
                'Battery\ Temperature\ -\ Last\ 24\ Hours', 'end-1day', \
                 0, 0, 2, autoScale)
    createGraph('24hr_ambtemp', 'ATMP', 'deg\ C', 
                'Ambient\ Temperature\ -\ Last\ 24\ Hours', 'end-1day', \
                 0, 0, 2, autoScale)

    # 4 week stock charts

    createGraph('4wk_current', 'CUR', 'mA', 
                'Current\ -\ Last\ 4\ Weeks', 'end-4weeks', 0, 0, 2, autoScale)
    createGraph('4wk_voltage', 'VOLT', 'V', 
                'Voltage\ -\ Last\ 4\ Weeks', 'end-4weeks', 0, 0, 2, autoScale)
    createGraph('4wk_power', 'PWR', 'mW', 
                'Power\ -\ Last\ 4\ Weeks', 'end-4weeks', 0, 0, 2, autoScale)
    createGraph('4wk_battemp', 'BTMP', 'deg\ C', 
                'Battery\ Temperature\ -\ Last\ 4\ Weeks', 'end-4weeks', \
                 0, 0, 2, autoScale)
    createGraph('4wk_ambtemp', 'ATMP', 'deg\ C', 
                'Ambient\ Temperature\ -\ Last\ 4\ Weeks', 'end-4weeks', \
                 0, 0, 2, autoScale)

    # 12 month stock charts

    createGraph('12m_current', 'CUR', 'mA', 
                'Current\ -\ Past\ Year', 'end-12months', 0, 0, 2, autoScale)
    createGraph('12m_voltage', 'VOLT', 'V', 
                'Voltage\ -\ Past\ Year', 'end-12months', 0, 0, 2, autoScale)
    createGraph('12m_power', 'PWR', 'mW', 
                'Power\ -\ Past\ Year', 'end-12months', 0, 0, 2, autoScale)
    createGraph('12m_battemp', 'BTMP', 'deg\ C', 
                'Battery\ Temperature\ -\ Past\ Year', 'end-12months', \
                 0, 0, 2, autoScale)
    createGraph('12m_ambtemp', 'ATMP', 'deg\ C', 
                'Ambient\ Temperature\ -\ Past\ Year', 'end-12months', \
                 0, 0, 2, autoScale)
##end def

def getCLarguments():
    """Get command line arguments.  There are three possible arguments
          -d turns on debug mode
          -v turns on verbose debug mode
          -t sets the sensor query interval
       Returns: nothing
    """
    global debugOption, verboseDebug, dataRequestInterval

    index = 1
    while index < len(sys.argv):
        if sys.argv[index] == '-d':
            debugOption = True
        elif sys.argv[index] == '-v':
            debugOption = True
            verboseDebug = True
        elif sys.argv[index] == '-p':
            try:
                dataRequestInterval = abs(int(sys.argv[index + 1]))
            except:
                print "invalid polling period"
                exit(-1)
            index += 1
        else:
            cmd_name = sys.argv[0].split('/')
            print "Usage: %s [-d] [-v] [-p seconds]" % cmd_name[-1]
            exit(-1)
        index += 1
##end def

def main():
    """Handles timing of events and acts as executive routine managing
       all other functions.
       Parameters: none
       Returns: nothing
    """
    global dataRequestInterval

    signal.signal(signal.SIGTERM, terminateAgentProcess)

    print '%s starting up node power agent process' % \
                  (getTimeStamp())

    # last time output JSON file updated
    lastDataRequestTime = -1
    # last time charts generated
    lastChartUpdateTime = - 1
    # last time the rrdtool database updated
    lastDatabaseUpdateTime = -1

    ## Get command line arguments.
    getCLarguments()

    ## Exit with error if rrdtool database does not exist.
    if not os.path.exists(_RRD_FILE):
        print 'rrdtool database does not exist\n' \
              'use createArednsigRrd script to ' \
              'create rrdtool database\n'
        exit(1)
 
    ## main loop
    while True:

        currentTime = time.time() # get current time in seconds

        # Every web update interval request data from the aredn
        # node and process the received data.
        if currentTime - lastDataRequestTime > dataRequestInterval:
            lastDataRequestTime = currentTime
            dData = {}
            result = True

            # Get the data from the sensors.
            result =getSensorData(dData)
 
            # If get data successful, write data to data files.
            if result:
                result = writeOutputDataFile(dData)

            # At the rrdtool database update interval, update the database.
            if currentTime - lastDatabaseUpdateTime > \
                    _DATABASE_UPDATE_INTERVAL:   
                lastDatabaseUpdateTime = currentTime
                ## Update the round robin database with the parsed data.
                if result:
                    updateDatabase(dData)

        # At the chart generation interval, generate charts.
        if currentTime - lastChartUpdateTime > chartUpdateInterval:
            lastChartUpdateTime = currentTime
            p = multiprocessing.Process(target=generateGraphs, args=())
            p.start()

        # Relinquish processing back to the operating system until
        # the next update interval.

        elapsedTime = time.time() - currentTime
        if debugOption:
            if result:
                print "%s update successful:" % getTimeStamp(),
            else:
                print "%s update failed:" % getTimeStamp(),
            print "%6f seconds processing time\n" % elapsedTime 
        remainingTime = dataRequestInterval - elapsedTime
        if remainingTime > 0.0:
            time.sleep(remainingTime)
    ## end while
    return
## end def

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print '\n',
        terminateAgentProcess('KeyboardInterrupt','Module')