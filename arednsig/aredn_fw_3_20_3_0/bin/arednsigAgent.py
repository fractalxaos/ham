#!/usr/bin/python -u
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
#
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

import os
import urllib2
import sys
import signal
import subprocess
import multiprocessing
import time

_USER = os.environ['USER']
_HOSTNAME = os.uname()[1]

   ### DEFAULT AREDN NODE URL ###

# set url of the aredn node

_DEFAULT_AREDN_NODE_URL = "http://localnode:8080/cgi-bin/status"

    ### FILE AND FOLDER LOCATIONS ###

# folder for containing dynamic data objects
_DOCROOT_PATH = "/home/%s/public_html/arednsig/" % _USER
# folder for charts and output data file
_CHARTS_DIRECTORY = _DOCROOT_PATH + "dynamic/"
# location of data output file
_OUTPUT_DATA_FILE = _DOCROOT_PATH + "dynamic/arednsigOutputData.js"
# dummy output data file
_DUMMY_OUTPUT_FILE = _DOCROOT_PATH + "dynamic/nodeOnline.js"
# database that stores node data
_RRD_FILE = "/home/%s/database/arednsigData.rrd" % _USER

    ### GLOBAL CONSTANTS ###

# interval in minutes between data requests to the aredn node
_DEFAULT_DATA_REQUEST_INTERVAL = 1
# chart update interval in minutes
_CHART_UPDATE_INTERVAL = 10

# number seconds to wait for a response to HTTP request
_HTTP_REQUEST_TIMEOUT = 10
# max number of failed data requests allowed
_MAX_FAILED_DATA_REQUESTS = 0
# standard chart width in pixels
_CHART_WIDTH = 600
# standard chart height in pixels
_CHART_HEIGHT = 150
# Set this to True only if this server is intended to relay raw
# node data to a mirror server.
_RELAY_SERVER = False

   ### GLOBAL VARIABLES ###

# turn on or off of verbose debugging information
debugOption = False
verboseDebug = False

# The following two items are used for detecting system faults
# and aredn node online or offline status.

# count of failed attempts to get data from aredn node
failedUpdateCount = 0
# detected status of aredn node device
nodeOnline = True

# ip address of aredn node
arednNodeUrl = _DEFAULT_AREDN_NODE_URL
# frequency of data requests to aredn node
dataRequestInterval = _DEFAULT_DATA_REQUEST_INTERVAL
# chart update interval
chartUpdateInterval = _CHART_UPDATE_INTERVAL
# last node request time
lastDataPointTime = -1

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
    if os.path.exists(_DUMMY_OUTPUT_FILE):
       os.remove(_DUMMY_OUTPUT_FILE)
    # If the aredn node was previously online, then send
    # a message that we are now offline.
    if nodeOnline:
        print '%s aredn node offline' % getTimeStamp()
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
    if os.path.exists(_DUMMY_OUTPUT_FILE):
       os.remove(_DUMMY_OUTPUT_FILE)
    print '%s terminating arednsig agent process' % \
              (getTimeStamp())
    sys.exit(0)
##end def

  ###  PUBLIC METHODS  ###

def getArednNodeData():
    """Send http request to aredn node.  The response from the
       node contains the node signal data as unformatted ascii text.
       Parameters: none
       Returns: a string containing the node signal data if successful,
                or None if not successful
    """
    try:
        conn = urllib2.urlopen(arednNodeUrl, timeout=_HTTP_REQUEST_TIMEOUT)

        # Format received data into a single string.
        content = ""
        for line in conn:
            content += line.strip()
        del conn

    except Exception, exError:
        # If no response is received from the device, then assume that
        # the device is down or unavailable over the network.  In
        # that case return None to the calling function.
        print "%s http error: %s" % (getTimeStamp(), exError)
        return None

    if verboseDebug:
        print "http request successful: %d bytes" % len(content)

    return content
##end def

def parseNodeData(sData, dData):
    """Parse the node status page html from the aredn node
       into its component parts.  
       Parameters:
           sData - the string containing the data to be parsed
           dData - a dictionary object to contain the parsed data items
       Returns: True if successful, False otherwise
    """
    try:

        # Set search boundaries for signal data
        strBeginSearch = '<nobr>Signal/Noise/Ratio</nobr></th>' \
                         '<td valign=middle><nobr><big><b>'
        strEndSearch = 'dB'
        iBeginIndex = sData.find(strBeginSearch) + len(strBeginSearch)
        iEndIndex = sData.find(strEndSearch, iBeginIndex)

        # Exception if signal data not found
        if iBeginIndex == -1 or iEndIndex == -1:
            raise Exception("signal data not found in status page")

        # Extract signal data from html
        snr = sData[iBeginIndex:iEndIndex]
        snr = snr.replace(' ','')
        lsnr = snr.split('/')

        # Store time and signal data in dictionary object
        dData['time'] = getEpochSeconds(getTimeStamp())
        dData['signal'] = lsnr[0]
        dData['noise'] = lsnr[1]
        dData['snr'] = lsnr[2]
    
    except Exception, exError:
        print "%s parse failed: %s" % (getTimeStamp(), exError)
        return False

    if verboseDebug:
        print "parse successful"
    return True
##end def

def updateDatabase(dData):
    """
    Update the rrdtool database by executing an rrdtool system command.
    Format the command using the data extracted from the aredn node
    response.   
    Parameters: dData - dictionary object containing data items to be
                        written to the rr database file
    Returns: True if successful, False otherwise
    """
    # Format the rrdtool update command.
    strFmt = "rrdtool update %s %s:%s:%s:%s:%s:%s:%s:%s"
    strCmd = strFmt % (_RRD_FILE, dData['time'], dData['signal'], \
             dData['noise'], dData['snr'], '0', \
             '0', '0', '0')

    if verboseDebug:
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

def writeOutputDataFile(sData, dData):
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
    lastUpdate = time.strftime( "%m.%d.%Y %T", 
                                time.localtime(dData['time']) )
    sDate = "[{\"date\":\"%s\",\"period\":\"%s\"}]" % \
           (lastUpdate, chartUpdateInterval)
    try:
        fc = open(_DUMMY_OUTPUT_FILE, "w")
        fc.write(sDate)
        fc.close()
    except Exception, exError:
        print "%s write node file failed: %s" % (getTimeStamp(), exError)
        return False

    if _RELAY_SERVER:
        # Write the entire node data response to the output data file.
        try:
            fc = open(_OUTPUT_DATA_FILE, "w")
            fc.write(sData)
            fc.close()
        except Exception, exError:
            print "%s write output file failed: %s" % \
                  (getTimeStamp(), exError)
            return False
        if verboseDebug:
            print "write output data file: %d bytes" % len(sData)

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
        # Set status and send a message to the log if the node was
        # previously offline and is now online.
        if not nodeOnline:
            print '%s aredn node online' % getTimeStamp()
            nodeOnline = True
    else:
        # The last attempt failed, so update the failed attempts
        # count.
        failedUpdateCount += 1

    if failedUpdateCount > _MAX_FAILED_DATA_REQUESTS:
        # Max number of failed data requests, so set
        # node status to offline.
        setStatusToOffline()
##end def

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

    # The following will force creation of charts
    # of only signal strength and S/N charts.  Note that the following
    # data items appear constant and do not show variation with time:
    # noise level, rx mcs, rx rate, tx mcs, tx rate.  Therefore, until
    # these parameters are demonstrated to vary in time, there is no point
    # in creating the charts for these data items.
    createAllCharts = False

    # 24 hour stock charts

    createGraph('24hr_signal', 'S', 'dBm', 
                'RSSI\ -\ Last\ 24\ Hours', 'end-1day', 0, 0, 2, autoScale)
    createGraph('24hr_snr', 'SNR', 'dB', 
                'SNR\ -\ Last\ 24\ Hours', 'end-1day', 0, 0, 2, autoScale)

    # 4 week stock charts

    createGraph('4wk_signal', 'S', 'dBm', 
                'RSSI\ -\ Last\ 4\ Weeks', 'end-4weeks', 0, 0, 2, autoScale)
    createGraph('4wk_snr', 'SNR', 'dB', 
                'SNR\ -\ Last\ 4\ Weeks', 'end-4weeks', 0, 0, 2, autoScale)

    # 12 month stock charts

    createGraph('12m_signal', 'S', 'dBm', 
                'RSSI\ -\ Past\ Year', 'end-12months', 0, 0, 2, autoScale)
    createGraph('12m_snr', 'SNR', 'dB', 
                'SNR\ -\ Past\ Year', 'end-12months', 0, 0, 2, autoScale)

    if debugOption:
        #print # print a blank line to improve readability when in debug mode
        pass
##end def

def getCLarguments():
    """Get command line arguments.  There are four possible arguments
          -d turns on debug mode
          -v turns on verbose debug mode
          -t sets the aredn node query interval
          -u sets the url of the aredn nodeing device
       Returns: nothing
    """
    global debugOption, verboseDebug, dataRequestInterval, \
           arednNodeUrl

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
        elif sys.argv[index] == '-u':
            arednNodeUrl = sys.argv[index + 1]
            index += 1
        else:
            cmd_name = sys.argv[0].split('/')
            print "Usage: %s [-d] [-v] [-p seconds] [-u url]" % cmd_name[-1]
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

    print '%s starting up arednsig agent process' % \
                  (getTimeStamp())

    # last time output JSON file updated
    lastDataRequestTime = -1
    # last time charts generated
    lastChartUpdateTime = - 1

    ## Get command line arguments.
    getCLarguments()

    requestIntervalSeconds = dataRequestInterval * 60 # convert to seconds
    chartUpdateIntervalSeconds = chartUpdateInterval * 60 # charts interval

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
        if currentTime - lastDataRequestTime > requestIntervalSeconds:
            lastDataRequestTime = currentTime
            dData = {}
            result = True

            # Get the data string from the device.
            sData = getArednNodeData()
            # If the first http request fails, try one more time.
            if sData == None:
                result = False

            # If successful parse the data.
            if result:
                result = parseNodeData(sData, dData)
           
            # If parse successful, write data to data files.
            if result:
                result = updateDatabase(dData)

            if result:
                writeOutputDataFile(sData, dData)

            # Set the node status to online or offline depending on the
            # success or failure of the above operations.
            setNodeStatus(result)

        # At the chart generation interval, generate charts.
        if currentTime - lastChartUpdateTime > chartUpdateIntervalSeconds:
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
        remainingTime = requestIntervalSeconds - elapsedTime
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
