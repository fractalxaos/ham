#!/usr/bin/python3 -u
# The -u option above turns off block buffering of python output. This 
# assures that each error message gets individually printed to the log file.
#
# Module: arednsigAgent.py
#
# Description: This module acts as an agent between the aredn node
# and aredn mest services.  The agent periodically sends an http
# request to the aredn node, processes the response from
# the node, and performs a number of operations:
#     - conversion of data items
#     - update a round robin (rrdtool) database with the node data
#     - periodically generate graphic charts for display in html documents
#     - write the processed node status to a JSON file for use by html
#       documents
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
#   * v20 released 11 Jan 2020 by J L Owrey; first release
#   * v21 released 13 Feb 2020 by J L Owrey; fixed bug occuring when node
#     powers on and signal data memory is empty.  Data points with N/A data
#     are discarded.
#   * v22 released 31 Mar 2020 by J L Owrey; upgraded for compatibility with
#     Aredn firmware version 3.20.3.0.  This agent now downloads the node's
#     status page and parsed the signal data from the html.
#   * v23 released 11 Jun 2021 by J L Owrey; remove unused code.
#   * v24 released 14 Jun 2021 by J L Owrey; minor revisions
#   * v25 released 9 Jul 2021 by J L Owrey; improved handling of
#         node status function
#
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

import os
import sys
import signal
import multiprocessing
import time
import json
from urllib.request import urlopen
import rrdbase

   ### ENVIRONMENT ###

_USER = os.environ['USER']
_SERVER_MODE = "primary"

   ### DEFAULT AREDN NODE URL ###

_DEFAULT_AREDN_NODE_URL = "http://localnode.local.mesh/cgi-bin/status"

    ### FILE AND FOLDER LOCATIONS ###

# folder for containing dynamic data objects
_DOCROOT_PATH = "/home/%s/public_html/arednsig/" % _USER
# folder for charts and output data file
_CHARTS_DIRECTORY = _DOCROOT_PATH + "dynamic/"
# location of data output file
_OUTPUT_DATA_FILE = _DOCROOT_PATH + "dynamic/arednsigData.js"
# database that stores node data
_RRD_FILE = "/home/%s/database/arednsigData.rrd" % _USER

    ### GLOBAL CONSTANTS ###

# maximum number of failed data requests allowed
_MAX_FAILED_DATA_REQUESTS = 2
# maximum number of http request retries  allowed
_MAX_HTTP_RETRIES = 3
# delay time between http request retries
_HTTP_RETRY_DELAY = 1.1199
# interval in seconds between data requests
_DEFAULT_DATA_REQUEST_INTERVAL = 60
# number seconds to wait for a response to HTTP request
_HTTP_REQUEST_TIMEOUT = 3

# interval in seconds between database updates
_DATABASE_UPDATE_INTERVAL = 60
# chart update interval in seconds
_CHART_UPDATE_INTERVAL = 600
# standard chart width in pixels
_CHART_WIDTH = 600
# standard chart height in pixels
_CHART_HEIGHT = 150
# Set this to True only if this server is intended to relay raw

   ### GLOBAL VARIABLES ###

# turn on or off of verbose debugging information
verboseMode = False
debugMode = False
reportUpdateFails = False

# The following two items are used for detecting system faults
# and aredn node online or offline status.

# count of failed attempts to get data from aredn node
failedUpdateCount = 0
httpRetries = 0
nodeOnline = False

# ip address of aredn node
arednNodeUrl = _DEFAULT_AREDN_NODE_URL
# frequency of data requests to aredn node
dataRequestInterval = _DEFAULT_DATA_REQUEST_INTERVAL
# chart update interval
chartUpdateInterval = _CHART_UPDATE_INTERVAL

# rrdtool database interface handler instance
rrdb = None

  ###  PRIVATE METHODS  ###

def getTimeStamp():
    """
    Set the error message time stamp to the local system time.
    Parameters: none
    Returns: string containing the time stamp
    """
    return time.strftime( "%m/%d/%Y %T", time.localtime() )
##end def

def setStatusToOffline():
    """Set the detected status of the aredn node to
       "offline" and inform downstream clients by removing input
       and output data files.
       Parameters: none
       Returns: nothing
    """
    global nodeOnline

    # Inform downstream clients by removing output data file.
    if os.path.exists(_OUTPUT_DATA_FILE):
       os.remove(_OUTPUT_DATA_FILE)
    # If the aredn node was previously online, then send
    # a message that we are now offline.
    if nodeOnline:
        print('%s aredn node offline' % getTimeStamp())
    nodeOnline = False
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
    print('%s terminating arednsig agent process' % getTimeStamp())
    sys.exit(0)
##end def

  ###  PUBLIC METHODS  ###

def getNodeData(dData):
    """Send http request to aredn node.  The response from the
       node contains the node signal data as unformatted ascii text.
       Parameters: none
       Returns: True if successful,
                or False if not successful
    """
    global httpRetries

    try:
        currentTime = time.time()
        response = urlopen(arednNodeUrl, timeout=_HTTP_REQUEST_TIMEOUT)
        requestTime = time.time() - currentTime

        content = response.read().decode('utf-8')
        content = content.replace('\n', '')
        content = content.replace('\r', '')
        if content == "":
            raise Exception("empty response")
        
    except Exception as exError:
        # If no response is received from the device, then assume that
        # the device is down or unavailable over the network.  In
        # that case return None to the calling function.
        httpRetries += 1

        if reportUpdateFails:
            print("%s " % getTimeStamp(), end='')
        if reportUpdateFails or verboseMode:
            print("http request failed (%d): %s" % \
                (httpRetries, exError))

        if httpRetries > _MAX_HTTP_RETRIES:
            httpRetries = 0
            return False
        else:
            time.sleep(_HTTP_RETRY_DELAY)
            return getNodeData(dData)
    ## end try

    if debugMode:
        print(content)
    if verboseMode:
        print("http request successful: "\
              "%.4f seconds" % requestTime)

    httpRetries = 0
    dData['content'] = content
    return True
##end def

def parseDataString(dData):
    """Parse the node signal data JSON string from the aredn node
       into its component parts.  
       Parameters:
           sData - the string containing the data to be parsed
           dData - a dictionary object to contain the parsed data items
       Returns: True if successful, False otherwise
    """
    sData = dData.pop('content')
    try:
        strBeginSearch = '<nobr>Signal/Noise/Ratio</nobr></th>' \
                         '<td valign=middle><nobr><big><b>'
        strEndSearch = 'dB</b>'

        iBeginIndex = sData.find(strBeginSearch) + len(strBeginSearch)
        iEndIndex = sData.find(strEndSearch, iBeginIndex)
        #print("search params: %d, %d" % (iBeginIndex, iEndIndex))

        if iBeginIndex == -1 or iEndIndex == -1:
            raise Exception("signal data not found in status page")

        snr = sData[iBeginIndex:iEndIndex]
        snr = snr.replace(' ','')
        lsnr = snr.split('/')

        dData['signal'] = lsnr[0]
        dData['noise'] = lsnr[1]
        dData['snr'] = lsnr[2]
    except Exception as exError:
        print("%s parse failed: %s" % (getTimeStamp(), exError))
        return False
    ## end try

    # Add status information to dictionary object.
    dData['date'] = getTimeStamp()
    dData['chartUpdateInterval'] = chartUpdateInterval
    dData['dataRequestInterval'] = dataRequestInterval
    dData['serverMode'] = _SERVER_MODE

    return True
##end def

def writeOutputFile(dData):
    """Write node data items to the output data file, formatted as 
       a Javascript file.  This file may then be accessed and used by
       by downstream clients, for instance, in HTML documents.
       Parameters:
           sData - a string object containing the data to be written
                   to the output data file
       Returns: True if successful, False otherwise
    """
    # Write file for use by html clients.  The following two
    # data items are sent to the client file.
    #    * The last database update date and time
    #    * The data request interval

    # Format data into a JSON string.
    jsData = json.loads("{}")
    try:
        for key in dData:
            jsData.update({key:dData[key]})
        sData = "[%s]" % json.dumps(jsData)
    except Exception as exError:
        print("%s writeOutputFile: %s" % (getTimeStamp(), exError))
        return False

    if debugMode:
        print(sData)

    try:
        fc = open(_OUTPUT_DATA_FILE, "w")
        fc.write(sData)
        fc.close()
    except Exception as exError:
        print("%s write output file failed: %s" % (getTimeStamp(), exError))
        return False

    return True
## end def

def setNodeStatus(updateSuccess):
    """Detect if aredn node is offline or not available on
       the network. After a set number of attempts to get data
       from the node set a flag that the node is offline.
       Parameters:
           updateSuccess - a boolean that is True if data request
                           successful, False otherwise
       Returns: nothing
    """
    global failedUpdateCount, nodeOnline

    if updateSuccess:
        failedUpdateCount = 0
        # Set status and send a message to the log if the device
        # previously offline and is now online.
        if not nodeOnline:
            print('%s aredn node online' % getTimeStamp())
            nodeOnline = True
        return
    else:
        # The last attempt failed, so update the failed attempts
        # count.
        failedUpdateCount += 1

    if failedUpdateCount == _MAX_FAILED_DATA_REQUESTS:
        # Max number of failed data requests, so set
        # device status to offline.
        setStatusToOffline()
##end def

    ### GRAPH FUNCTIONS ###

def generateGraphs():
    """Generate graphs for display in html documents.
       Parameters: none
       Returns: nothing
    """
    autoScale = False

    # The following will force creation of charts
    # of only signal strength and S/N charts.  Note that the following
    # data items appear constant and do not show variation with time:
    # noise level, rx mcs, rx rate, tx mcs, tx rate.  Therefore, until
    # these parameters are demonstrated to vary in time, there is no point
    # in creating the charts for these data items.
    createAllCharts = False

    # 24 hour stock charts


    #### REPLACE WITH createRadGraph ####


    rrdb.createAutoGraph('24hr_signal', 'S', 'dBm', 
                'RSSI\ -\ Last\ 24\ Hours', 'end-1day', 0, 0, 2, autoScale)
    rrdb.createAutoGraph('24hr_snr', 'SNR', 'dB', 
                'SNR\ -\ Last\ 24\ Hours', 'end-1day', 0, 0, 2, autoScale)

    # 4 week stock charts

    rrdb.createAutoGraph('4wk_signal', 'S', 'dBm', 
                'RSSI\ -\ Last\ 4\ Weeks', 'end-4weeks', 0, 0, 2, autoScale)
    rrdb.createAutoGraph('4wk_snr', 'SNR', 'dB', 
                'SNR\ -\ Last\ 4\ Weeks', 'end-4weeks', 0, 0, 2, autoScale)

    # 12 month stock charts

    rrdb.createAutoGraph('12m_signal', 'S', 'dBm', 
                'RSSI\ -\ Past\ Year', 'end-12months', 0, 0, 2, autoScale)
    rrdb.createAutoGraph('12m_snr', 'SNR', 'dB', 
                'SNR\ -\ Past\ Year', 'end-12months', 0, 0, 2, autoScale)

    if verboseMode:
        #print() # print a blank line to improve readability when in debug mode
        pass
##end def

def getCLarguments():
    """Get command line arguments.  There are four possible arguments
          -d turns on debug mode
          -v turns on verbose debug mode
          -p sets the aredn node query interval
          -u sets the url of the aredn nodeing device
       Returns: nothing
    """
    global verboseMode, debugMode, dataRequestInterval, \
           arednNodeUrl, reportUpdateFails

    index = 1
    while index < len(sys.argv):
        if sys.argv[index] == '-v':
            verboseMode = True
        elif sys.argv[index] == '-d':
            verboseMode = True
            debugMode = True
        elif sys.argv[index] == '-r':
            reportUpdateFails = True

        # Update period and url options
        elif sys.argv[index] == '-p':
            try:
                dataRequestInterval = abs(float(sys.argv[index + 1]))
            except:
                print("invalid polling period")
                exit(-1)
            index += 1
        elif sys.argv[index] == '-u':
            arednNodeUrl = sys.argv[index + 1]
            if arednNodeUrl.find('http://') < 0:
                arednNodeUrl = 'http://' + arednNodeUrl
            index += 1
        else:
            cmd_name = sys.argv[0].split('/')
            print("Usage: %s [-v|d] [-p seconds] [-u url]" % cmd_name[-1])
            exit(-1)
        index += 1
##end def

def setup():
    """Handles timing of events and acts as executive routine managing
       all other functions.
       Parameters: none
       Returns: nothing
    """
    global rrdb

    ## Get command line arguments.
    getCLarguments()

    print('======================================================')
    print('%s starting up arednsig agent process' % \
                  (getTimeStamp()))

    ## Exit with error if rrdtool database does not exist.
    if not os.path.exists(_RRD_FILE):
        print('rrdtool database does not exist\n' \
              'use createArednsigRrd script to ' \
              'create rrdtool database\n')
        exit(1)

    signal.signal(signal.SIGTERM, terminateAgentProcess)
    signal.signal(signal.SIGINT, terminateAgentProcess)

    # Define object for calling rrdtool database functions.
    rrdb = rrdbase.rrdbase( _RRD_FILE, _CHARTS_DIRECTORY, _CHART_WIDTH, \
                            _CHART_HEIGHT, verboseMode, debugMode )
## end def

def loop():
    # last time output JSON file updated
    lastDataRequestTime = -1
    # last time charts generated
    lastChartUpdateTime = -1
    # last time the rrdtool database updated
    lastDatabaseUpdateTime = -1
 
    ## main loop
    while True:

        currentTime = time.time() # get current time in seconds

        # Every web update interval request data from the aredn
        # node and process the received data.
        if currentTime - lastDataRequestTime > dataRequestInterval:
            lastDataRequestTime = currentTime
            dData = {}

            # Get the data string from the device.
            result = getNodeData(dData)

            # If successful parse the data.
            if result:
                result = parseDataString(dData)

            # If parse successful, write data output data file.
            if result:
                writeOutputFile(dData)

            # At the rrdtool database update interval, update the database.
            if result and (currentTime - lastDatabaseUpdateTime > \
                           _DATABASE_UPDATE_INTERVAL):   
                lastDatabaseUpdateTime = currentTime
                # If write output file successful, update the database.
                if result:
                    result = rrdb.updateDatabase(dData['date'], \
                             dData['signal'], dData['noise'], dData['snr'], \
                            '0', '0', '0', '0')

            # Set the node status to online or offline depending on the
            # success or failure of the above operations.
            setNodeStatus(result)


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
                print("update successful: %s sec\n" % elapsedTime)
            else:
                print("update failed: %s sec\n" % elapsedTime)
        remainingTime = dataRequestInterval - elapsedTime
        if remainingTime > 0.0:
            time.sleep(remainingTime)
    ## end while
## end def

if __name__ == '__main__':
    setup()
    loop()

