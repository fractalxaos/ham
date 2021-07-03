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
#   * v11 released 02 July 2021 by J L Owrey; improved sensor fault
#     handling; improved code readability
#
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

# Import required python libraries.
import os
import sys
import signal
import subprocess
import multiprocessing
import time
import json

# Import sensor libraries.
import ina260 # power sensor
import tmp102 # temperature sensor

    ### ENVIRONMENT ###
_USER = os.environ['USER']

    ### SENSOR BUS ADDRESSES ###

# Set bus addresses of sensors.
_PWR_SENSOR_ADDR = 0X40
_BAT_TMP_SENSOR_ADDR = 0x48
_AMB_TMP_SENSOR_ADDR = 0x4B
# Set bus selector.
_BUS_NUMBER = 1

    ### FILE AND FOLDER LOCATIONS ###

# folder to contain html
_DOCROOT_PATH = "/home/%s/public_html/power/" % _USER
# folder to contain charts and output data file
_CHARTS_DIRECTORY = _DOCROOT_PATH + "dynamic/"
# location of JSON output data file
_OUTPUT_DATA_FILE = _DOCROOT_PATH + "dynamic/powerData.js"
# database that stores node data
_RRD_FILE = "/home/%s/database/powerData.rrd" % _USER

    ### GLOBAL CONSTANTS ###

# sensor data request interval in seconds
_DEFAULT_SENSOR_POLLING_INTERVAL = 2
# rrdtool database update interval in seconds
_DATABASE_UPDATE_INTERVAL = 30
# max number of failed attempts to get sensor data
_MAX_FAILED_DATA_REQUESTS = 2

# chart update interval in seconds
_CHART_UPDATE_INTERVAL = 600
# standard chart width in pixels
_CHART_WIDTH = 600
# standard chart height in pixels
_CHART_HEIGHT = 150
# chart average line color
_AVERAGE_LINE_COLOR = '#006600'

   ### GLOBAL VARIABLES ###

# turns on or off extensive debugging messages
debugMode = False
verboseMode = False

# frequency of data requests to sensors
dataRequestInterval = _DEFAULT_SENSOR_POLLING_INTERVAL
# how often charts get updated
chartUpdateInterval = _CHART_UPDATE_INTERVAL
# number of failed attempts to get sensor data
failedUpdateCount = 0
# sensor status
deviceOnline = False

# Create sensor objects.  This also initialzes each sensor.
power = ina260.ina260(_PWR_SENSOR_ADDR, _BUS_NUMBER)
battemp = tmp102.tmp102(_BAT_TMP_SENSOR_ADDR, _BUS_NUMBER)
ambtemp = tmp102.tmp102(_AMB_TMP_SENSOR_ADDR, _BUS_NUMBER)

  ###  PRIVATE METHODS  ###

def getTimeStamp():
    """
    Get the local time and format as a text string.
    Parameters: none
    Returns: string containing the time stamp
    """
    return time.strftime( "%m/%d/%Y %T", time.localtime() )
## end def

def getEpochSeconds(sTime):
    """
    Convert the time stamp to seconds since 1/1/1970 00:00:00.
    Parameters: 
        sTime - the time stamp to be converted must be formatted
                   as %m/%d/%Y %H:%M:%S
    Returns: epoch seconds
    """
    try:
        t_sTime = time.strptime(sTime, '%m/%d/%Y %H:%M:%S')
    except Exception as exError:
        print('%s getEpochSeconds: %s' % (getTimeStamp(), exError))
        return None
    tSeconds = int(time.mktime(t_sTime))
    return tSeconds
## end def

def setStatusToOffline():
    """Set the detected status of the device to
       "offline" and inform downstream clients by removing input
       and output data files.
       Parameters: none
       Returns: nothing
    """
    global deviceOnline

    # Inform downstream clients by removing output data file.
    if os.path.exists(_OUTPUT_DATA_FILE):
       os.remove(_OUTPUT_DATA_FILE)
    # If the sensor or  device was previously online, then send
    # a message that we are now offline.
    if deviceOnline:
        print('%s device offline' % getTimeStamp())
    deviceOnline = False
##end def

def terminateAgentProcess(signal, frame):
    """Send a message to log when the agent process gets killed
       by the operating system.  Inform downstream clients
       by removing input and output data files.
       Parameters:
           signal, frame - dummy parameters
       Returns: nothing
    """
    print('%s terminating agent process' % getTimeStamp())
    setStatusToOffline()
    sys.exit(0)
##end def

  ###  PUBLIC METHODS  ###

def getSensorData(dData):
    """
    Poll sensors for data. Store the data in a dictionary object for
    use by other subroutines.  The dictionary object passed in should
    an empty dictionary, i.e., dData = { }.
    Parameters: dData - a dictionary object to contain the sensor data
    Returns: True if successful, False otherwise
    """
    dData["time"] = getTimeStamp()
 
    try:
        dData["current"] = power.getCurrent()
        dData["voltage"] = power.getVoltage()
        dData["power"] = power.getPower()
        dData["battemp"] = battemp.getTempF()
        dData["ambtemp"] = ambtemp.getTempF()
    except Exception as exError:
        print("%s sensor error: %s" % (getTimeStamp(), exError))
        return False

    return True
## end def

def writeOutputFile(dData):
    """
    Write sensor data items to the output data file, formatted as 
    a Javascript file.  This file may then be requested and used by
    by downstream clients, for instance, an HTML document.
    Parameters:
        dData - a dictionary containing the data to be written
                   to the output data file
        Returns: True if successful, False otherwise
    """
    # Write a JSON formatted file for use by html clients.  The following
    # data items are sent to the client file.
    #    * The last database update date and time
    #    * The data request interval
    #    * The sensor values

    # Create a JSON formatted string from the sensor data.
    jsData = json.loads("{}")
    try:
        for key in dData:
            jsData.update({key:dData[key]})
        jsData.update({"chartUpdateInterval": chartUpdateInterval})
        sData = "[%s]" % json.dumps(jsData)
    except Exception as exError:
        print("%s writeOutputFile: %s" % (getTimeStamp(), exError))
        return False

    if debugMode:
        print(sData)

    # Write the JSON formatted data to the output data file.

    try:
        fc = open(_OUTPUT_DATA_FILE, "w")
        fc.write(sData)
        fc.close()
    except Exception as exError:
        print("%s write output file failed: %s" % \
              (getTimeStamp(), exError))
        return False

    return True
## end def

def setStatus(updateSuccess):
    """Detect if device is offline or not available on
       the network. After a set number of attempts to get data
       from the device set a flag that the device is offline.
       Parameters:
           updateSuccess - a boolean that is True if data request
                           successful, False otherwise
       Returns: nothing
    """
    global failedUpdateCount, deviceOnline

    if updateSuccess:
        failedUpdateCount = 0
        # Set status and send a message to the log if the device
        # previously offline and is now online.
        if not deviceOnline:
            print('%s device online' % getTimeStamp())
            deviceOnline = True
    else:
        # The last attempt failed, so update the failed attempts
        # count.
        failedUpdateCount += 1

    if failedUpdateCount >= _MAX_FAILED_DATA_REQUESTS:
        # Max number of failed data requests, so set
        # device status to offline.
        setStatusToOffline()
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

    if debugMode:
        print("%s" % strCmd) # DEBUG

    # Run the command as a subprocess.
    try:
        subprocess.check_output(strCmd, shell=True, \
            stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exError:
        print("%s: rrdtool update failed: %s" % \
            (getTimeStamp(), exError.output))
        return False

    if verboseMode and not debugMode:
        print("database updated")

    return True
## end def

def createGraph(fileName, dataItem, gLabel, gTitle, gStart,
                lower=0, upper=0, trendLine=0, scaleFactor=1,
                autoScale=True, alertLine=""):
    """
    Uses rrdtool to create a graph of specified sensor data item.
    Parameters:
        fileName - name of file containing the graph
        dataItem - data item to be graphed
        gLabel - string containing a graph label for the data item
        gTitle - string containing a title for the graph
        gStart - beginning time of the graphed data
        lower - lower bound for graph ordinate #NOT USED
        upper - upper bound for graph ordinate #NOT USED
        trendLine 
            0, show only graph data
            1, show only a trend line
            2, show a trend line and the graph data
        scaleFactor - amount to pre-scale the data before charting
            the data [default=1]
        autoScale - if True, then use vertical axis auto scaling
            (lower and upper parameters must be zero)
        alertLine - value for which to print a critical
            low voltage alert line on the chart. If not provided
            alert line will not be printed.
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
    strCmd += "DEF:rSeries=%s:%s:LAST " % (_RRD_FILE, dataItem)
    strCmd += "CDEF:dSeries=rSeries,%s,/ " % (scaleFactor)

    if trendLine == 0:
        strCmd += "LINE1:dSeries#0400ff "
    elif trendLine == 1:
        strCmd += "CDEF:smoothed=dSeries,%s,TREND LINE2:smoothed%s " \
                  % (trendWindow[gStart], _AVERAGE_LINE_COLOR)
    elif trendLine == 2:
        strCmd += "LINE1:dSeries#0400ff "
        strCmd += "CDEF:smoothed=dSeries,%s,TREND LINE2:smoothed%s " \
                  % (trendWindow[gStart], _AVERAGE_LINE_COLOR)

    if alertLine != "":
        strCmd += "HRULE:%s#FF0000:Critical\ Low\ Voltage " % (alertLine)
     
    if debugMode:
        print("%s\n" % strCmd) # DEBUG
    
    # Run the formatted rrdtool command as a subprocess.
    try:
        result = subprocess.check_output(strCmd, \
                     stderr=subprocess.STDOUT,   \
                     shell=True)
    except subprocess.CalledProcessError as exError:
        print("rrdtool graph failed: %s" % (exError.output))
        return False

    if verboseMode and not debugMode:
        print("rrdtool graph: %s" % result.decode('utf-8'))
    return True

## end def

def generateGraphs():
    """
    Generate graphs for display in html documents.
    Parameters: none
    Returns: nothing
    """

    # 24 hour stock charts

    createGraph('24hr_current', 'CUR', 'Amps',
                'Current\ -\ Last\ 24\ Hours', 'end-1day', \
                0, 0, 2, 1000)
    createGraph('24hr_voltage', 'VOLT', 'Volts',
                'Voltage\ -\ Last\ 24\ Hours', 'end-1day', \
                9, 15, 0, 1, True, 11)
    createGraph('24hr_power', 'PWR', 'Watts', 
                'Power\ -\ Last\ 24\ Hours', 'end-1day', \
                0, 0, 2, 1000)
    createGraph('24hr_battemp', 'BTMP', 'deg\ F', 
                'Battery\ Temperature\ -\ Last\ 24\ Hours', 'end-1day', \
                0, 0, 0)
    createGraph('24hr_ambtemp', 'ATMP', 'deg\ F', 
                'Ambient\ Temperature\ -\ Last\ 24\ Hours', 'end-1day', \
                0, 0, 0)

    # 4 week stock charts

    createGraph('4wk_current', 'CUR', 'Amps',
                'Current\ -\ Last\ 4\ Weeks', 'end-4weeks', \
                0, 0, 2, 1000)
    createGraph('4wk_voltage', 'VOLT', 'Volts',
                'Voltage\ -\ Last\ 4\ Weeks', 'end-4weeks', \
                9, 15, 0, 1, True, 11)
    createGraph('4wk_power', 'PWR', 'Watts', 
                'Power\ -\ Last\ 4\ Weeks', 'end-4weeks', \
                0, 0, 2, 1000)
    createGraph('4wk_battemp', 'BTMP', 'deg\ F', 
                'Battery\ Temperature\ -\ Last\ 4\ Weeks', 'end-4weeks', \
                0, 0, 2)
    createGraph('4wk_ambtemp', 'ATMP', 'deg\ F', 
                'Ambient\ Temperature\ -\ Last\ 4\ Weeks', 'end-4weeks', \
                0, 0, 2)

    # 12 month stock charts

    createGraph('12m_current', 'CUR', 'Amps',
                'Current\ -\ Past\ Year', 'end-12months', \
                0, 0, 2, 1000)
    createGraph('12m_voltage', 'VOLT', 'Volts',
                'Voltage\ -\ Past\ Year', 'end-12months', \
                9, 15, 0, 1, True, 11)
    createGraph('12m_power', 'PWR', 'Watts', 
                'Power\ -\ Past\ Year', 'end-12months', \
                0, 0, 2, 1000)
    createGraph('12m_battemp', 'BTMP', 'deg\ F', 
                'Battery\ Temperature\ -\ Past\ Year', 'end-12months', \
                0, 0, 2)
    createGraph('12m_ambtemp', 'ATMP', 'deg\ F', 
                'Ambient\ Temperature\ -\ Past\ Year', 'end-12months', \
                0, 0, 2)
## end def

def getCLarguments():
    """
    Get command line arguments.  There are three possible arguments
        -d turns on debug mode
        -v turns on verbose mode
        -p sets the sensor query period
        -c sets the chart update period
    Returns: nothing
    """
    global debugMode, verboseMode, dataRequestInterval, chartUpdateInterval

    index = 1
    while index < len(sys.argv):
        if sys.argv[index] == '-v':
            verboseMode = True
        elif sys.argv[index] == '-d':
            debugMode = True
            verboseMode = True
        elif sys.argv[index] == '-p':
            try:
                dataRequestInterval = abs(int(sys.argv[index + 1]))
            except:
                print("invalid sensor query period")
                exit(-1)
            index += 1
        elif sys.argv[index] == '-c':
            try:
                chartUpdateInterval = abs(int(sys.argv[index + 1]))
            except:
                print("invalid chart update period")
                exit(-1)
            index += 1
        else:
            cmd_name = sys.argv[0].split('/')
            print("Usage: %s [-d | v] [-p seconds] [-c seconds]" \
                  % cmd_name[-1])
            exit(-1)
        index += 1
##end def

def main():
    """
    Handles timing of events and acts as executive routine managing
    all other functions.
    Parameters: none
    Returns: nothing
    """
    signal.signal(signal.SIGTERM, terminateAgentProcess)
    signal.signal(signal.SIGINT, terminateAgentProcess)

    # Log agent process startup time.
    print '===================\n'\
          '%s starting up node power agent process' % \
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
        print('rrdtool database does not exist\n' \
              'use createPowerRrd script to ' \
              'create rrdtool database\n')
        exit(1)
 
    ## main loop
    while True:

        currentTime = time.time() # get current time in seconds

        # Every data request interval read the sensors and process the
        # data from the sensors.
        if currentTime - lastDataRequestTime > dataRequestInterval:
            lastDataRequestTime = currentTime
            dData = {}

            # Get the data from the sensors.
            result =getSensorData(dData)
 
            # If get data successful, write data to data files.
            if result:
                result = writeOutputFile(dData)

            # At the rrdtool database update interval, update the database.
            if result and (currentTime - lastDatabaseUpdateTime > \
                           _DATABASE_UPDATE_INTERVAL):   
                lastDatabaseUpdateTime = currentTime
                ## Update the round robin database with the parsed data.
                result = updateDatabase(dData)

            setStatus(result)

        # At the chart generation interval, generate charts.
        if currentTime - lastChartUpdateTime > chartUpdateInterval:
            lastChartUpdateTime = currentTime
            p = multiprocessing.Process(target=generateGraphs, args=())
            p.start()
            
        # Relinquish processing back to the operating system until
        # the next update interval.

        elapsedTime = time.time() - currentTime
        if verboseMode:
            if result:
                print("update successful: %6f sec\n"
                      % elapsedTime)
            else:
                print("update failed: %6f sec\n"
                      % elapsedTime)
        remainingTime = dataRequestInterval - elapsedTime
        if remainingTime > 0.0:
            time.sleep(remainingTime)
    ## end while
    return
## end def

if __name__ == '__main__':
    main()
