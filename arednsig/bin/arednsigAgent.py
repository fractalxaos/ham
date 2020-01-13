#!/usr/bin/python -u
# The -u option above turns off block buffering of python output. This 
# assures that each error message gets individually printed to the log file.
#
# Module: arednsigAgent.py
#
# Description: This module acts as an agent between the aredn node
# and aredn mesh web services.  The agent periodically sends an http
# request to the aredn node, processes the response from
# the node, and performs a number of operations:
#     - conversion of data items
#     - update a round robin (rrdtool) database with the node data
#     - periodically generate graphic charts for display in html documents
#     - write the processed radmon data to a JSON file for use by html
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
#
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

import os
import urllib2
import sys
import signal
import subprocess
import multiprocessing
import time
import json

_USER = os.environ['USER']

   ### DEFAULT AREDN NODE URL ###

# ip address of the aredn node
_DEFAULT_AREDN_NODE_URL = "http://192.168.1.30/cgi-bin/signal.json"

    ### FILE AND FOLDER LOCATIONS ###

# folder for containing dynamic data objects
_DOCROOT_PATH = "/home/%s/public_html/arednsig/" % _USER
# folder for charts and output data file
_CHARTS_DIRECTORY = _DOCROOT_PATH + "dynamic/"
# location of data output file
_OUTPUT_DATA_FILE = _DOCROOT_PATH + "dynamic/arednsigOutputData.js"
# small size output data file for heartbeat signal to html docs
_SMALL_OUTPUT_FILE = _DOCROOT_PATH + "dynamic/nodeOnline.js"
# database that stores radmon data
_RRD_FILE = "/home/%s/database/arednsigData.rrd" % _USER

    ### GLOBAL CONSTANTS ###

# max number of failed data requests allowed
_MAX_FAILED_DATA_REQUESTS = 0
# interval in minutes between data requests to the aredn node
_DEFAULT_DATA_REQUEST_INTERVAL = 60
# number seconds to wait for a response to HTTP request
_HTTP_REQUEST_TIMEOUT = 10
# standard chart width in pixels
_CHART_WIDTH = 600
# standard chart height in pixels
_CHART_HEIGHT = 150

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

# network address of aredn node
arednNodeUrl = _DEFAULT_AREDN_NODE_URL
# frequency of data requests to aredn node
dataRequestInterval = _DEFAULT_DATA_REQUEST_INTERVAL
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

def getLastDataPointTime():
    """
    Get the timestamp of the most recent update to the round robin
    database.
    Parameters: none
    Returns: string epoch time stamp of the last rrd update
    """
    strCmd = "rrdtool lastupdate %s" % \
             (_RRD_FILE)

    # Run the command as a subprocess.
    try:
        result = subprocess.check_output(strCmd, shell=True,  \
                             stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError, exError:
        print "%s: rrdtool update failed: %s" % \
                    (getTimeStamp(), exError.output)
        return None

    # Return just the epoch time stamp of the last rrd update
    return int((result.split('\n')[-2]).split(':')[0])
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
    if os.path.exists(_SMALL_OUTPUT_FILE):
       os.remove(_SMALL_OUTPUT_FILE)
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
    if os.path.exists(_SMALL_OUTPUT_FILE):
       os.remove(_SMALL_OUTPUT_FILE)
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
        # If no response is received from the node, then assume that
        # the node is down or unavailable over the network.  In
        # that case return None to the calling function.
        print "%s http error: %s" % (getTimeStamp(), exError)
        return None

    if verboseDebug:
        print "http request successful: %d bytes" % len(content)

    return content
##end def

def parseNodeData(sData, ldData):
    """Parse the node  signal data JSON string from the aredn node
       into its component parts.  
       Parameters:
           sData - the string containing the data to be parsed
           ldData - a list object to contain the parsed data items
       Returns: True if successful, False otherwise
    """
    # Only interested in datapoints that have arrived during the
    # current update cycle defined by the data request interval.
    # The default is sixty minutes, and the node records a data point
    # once a minute.  Therefore, in the default case, extract the last
    # sixty data points from the node's response.  Otherwise, extract
    # a number of datapoints equal the the data request interval
    # (in minutes). 
    iTrail = int(dataRequestInterval)

    # The node response with json object containing 24 hours worth
    # of datapoints.  Each data point is, itself, a json object.
    # The following code converts the json object to a python list
    # object containing dictionary objects.  Each dictionary object
    # stores one data point.
    try:
        ldTmp = json.loads(sData[1:-1])
        ldTmp = ldTmp[-iTrail:]
        if len(ldTmp) != iTrail:
            raise Exception("truncated list")
    except Exception, exError:
        print "%s parse failed: %s" % (getTimeStamp(), exError)
        return False
       
    # Store the dictionary objects in the list object passed by
    # reference to this function.
    del ldData[:]
    for item in ldTmp:
        ldData.append(item)

    if verboseDebug:
        print "parse successful: %d data points" % len(ldData)
    return True
##end def

def convertData(ldData):
    """Convert individual node signal data items as necessary.
       Parameters:
           ldData - a list object containing the node signal data
       Returns: True if successful, False otherwise
    """
    # parse example string
    # {u'tx_mcs': u'15', u'rx_mcs': u'15', u'm': 47,
    #  u'label': u'01/10/2020 22:17:01', u'rx_rate': u'130',
    #  u'y': [-48, -95], u'x': 1578694621000, u'tx_rate': u'130'}
    #
    for item in ldData:
        try:
            # Convert data items to the required data types
            # (all integer in this case).  Change the dictionary
            # object keys to more friendly names.
            item['time'] = int(item.pop('x')) / 1000
            item['signal'] = int(item['y'][0])
            item['noise'] = int(item['y'][1])
            item['snr'] = int(item.pop('m'))
            item['rx_mcs'] = int(item.pop('rx_mcs'))
            item['tx_mcs'] = int(item.pop('tx_mcs'))
            item['rx_rate'] = int(item.pop('rx_rate'))
            item['tx_rate'] = int(item.pop('tx_rate'))
            item.pop('y')
            item.pop('label')
        except Exception, exError:
            print "%s convert data failed: %s" % (getTimeStamp(), exError)
            return False
    ##end for
    if verboseDebug:
        print "convert data successful"
    return True
##end def

def updateDatabase(ldData):
    """
    Update the rrdtool database by executing an rrdtool system command.
    Format the command using the data extracted from the aredn node
    response.   
    Parameters: ldData - a list object containing data items to be
                        written to the RRD file
    Returns: True if successful, False otherwise
    """
    updateCount = 0
    lastDataPointTime = getLastDataPointTime()

    if verboseDebug:
         print "updating database..."

    for item in ldData:
        # Throw out data points that have a time stamp earlier
        # than the last entry in the round-robin database (RRD).
        # rrdtool will throw an error in this case.
        if item['time'] <= lastDataPointTime:
            if verboseDebug:
                print "%s invalid timestamp: discarding data" % \
                      (getTimeStamp())
            continue

        # Format the rrdtool update command.
        strFmt = "rrdtool update %s %s:%s:%s:%s:%s:%s:%s:%s"
        strCmd = strFmt % (_RRD_FILE, item['time'], item['signal'], \
                 item['noise'], item['snr'], item['rx_mcs'], \
                 item['tx_mcs'], item['rx_rate'], item['tx_rate'])

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
        updateCount += 1
    ##end for

    if debugOption:
        print '%s added %d data points to database' % \
              (getTimeStamp(), updateCount)
    return True
##end def

def writeOutputDataFile(sData, ldData):
    """Write node data items to the output data file, formatted as 
       a Javascript file.  This file may then be accessed and used by
       by downstream clients, for instance, in HTML documents.
       Parameters:
           sData - a string object containing the data to be written
                   to the output data file
       Returns: True if successful, False otherwise
    """
    if verboseDebug:
        print "write output data file: %d bytes" % len(sData)

    # Write file for use by html clients.  The following two
    # data items are sent to the client file.
    #    * The last database update date and time
    #    * The data request interval
    lastUpdate = time.strftime( "%m.%d.%Y %T", 
                                time.localtime(ldData[-1]['time']) )
    sDate = "[{\"date\":\"%s\",\"period\":\"%s\"}]" % \
           (lastUpdate, dataRequestInterval)
    try:
        fc = open(_SMALL_OUTPUT_FILE, "w")
        fc.write(sDate)
        fc.close()
    except Exception, exError:
        print "%s write output file failed: %s" % (getTimeStamp(), exError)
        return False
    return True

    # Write the entire node data response to the output data file.
    try:
        fc = open(_OUTPUT_DATA_FILE, "w")
        fc.write(sData)
        fc.close()
    except Exception, exError:
        print "%s write output file failed: %s" % (getTimeStamp(), exError)
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
    """Uses rrdtool to create a graph of specified radmon data item.
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
        print "\n%s" % strCmd # DEBUG
    
    # Run the formatted rrdtool command as a subprocess.
    try:
        result = subprocess.check_output(strCmd, \
                     stderr=subprocess.STDOUT,   \
                     shell=True)
    except subprocess.CalledProcessError, exError:
        print "rrdtool graph failed: %s" % (exError.output)
        return False

    if debugOption:
        print "rrdtool graph: %s" % result,
    return True

##end def

def generateGraphs():
    """Generate graphs for display in html documents.
       Parameters: none
       Returns: nothing
    """
    autoScale = False

    createGraph('24hr_signal', 'S', 'dBm', 
                'RSSI\ -\ Last\ 24\ Hours', 'end-1day', 0, 0, 2, autoScale)
    createGraph('24hr_noise', 'N', 'dBm', 
                'Noise\ -\ Last\ 24\ Hours', 'end-1day', 0, 0, 2, autoScale)
    createGraph('24hr_snr', 'SNR', 'dB', 
                'SNR\ -\ Last\ 24\ Hours', 'end-1day', 0, 0, 2, autoScale)
    createGraph('24hr_rx_rate', 'RX_RATE', 'Mbps',
                'Rx\ Rate\ -\ Last\ 24\ Hours', 'end-1day', 0, 0, 2, autoScale)
    createGraph('24hr_tx_rate', 'TX_RATE', 'Mbps',
                'Tx\ Rate\ -\ Last\ 24\ Hours', 'end-1day', 0, 0, 2, autoScale)
    #createGraph('24hr_rx_mcs', 'RX_MCS', 'Index',
    #            'Rx\ MCS\ -\ Last\ 24\ Hours', 'end-1day', 0, 0, 2, autoScale)
    #createGraph('24hr_tx_mcs', 'TX_MCS', 'Index',
    #            'Tx\ MCS\ -\ Last\ 24\ Hours', 'end-1day', 0, 0, 2, autoScale)

    createGraph('4wk_signal', 'S', 'dBm', 
                'RSSI\ -\ Last\ 4\ Weeks', 'end-4weeks', 0, 0, 2, autoScale)
    createGraph('4wk_noise', 'N', 'dBm', 
                'Noise\ -\ Last\ 4\ Weeks', 'end-4weeks', 0, 0, 2, autoScale)
    createGraph('4wk_snr', 'SNR', 'dB', 
                'SNR\ -\ Last\ 4\ Weeks', 'end-4weeks', 0, 0, 2, autoScale)
    createGraph('4wk_rx_rate', 'RX_RATE', 'Mbps',
                'Rx\ Rate\ -\ Last\ 4\ Weeks', 'end-4weeks', 0, 0, 2, autoScale)
    createGraph('4wk_tx_rate', 'TX_RATE', 'Mbps',
                'Tx\ Rate\ -\ Last\ 4\ Weeks', 'end-4weeks', 0, 0, 2, autoScale)
    #createGraph('4wk_rx_mcs', 'RX_MCS', 'Index',
    #            'Rx\ MCS\ -\ Last\ 4\ Weeks', 'end-4weeks', 0, 0, 2, autoScale)
    #createGraph('4wk_tx_mcs', 'TX_MCS', 'Index',
    #            'Tx\ MCS\ -\ Last\ 4\ Weeks', 'end-4weeks', 0, 0, 2, autoScale)

    createGraph('12m_signal', 'S', 'dBm', 
                'RSSI\ -\ Past\ Year', 'end-12months', 0, 0, 2, autoScale)
    createGraph('12m_noise', 'N', 'dBm', 
                'Noise\ -\ Past\ Year', 'end-12months', 0, 0, 2, autoScale)
    createGraph('12m_snr', 'SNR', 'dB', 
                'SNR\ -\ Past\ Year', 'end-12months', 0, 0, 2, autoScale)
    createGraph('12m_rx_rate', 'RX_RATE', 'Mbps',
                'Rx\ Rate\ -\ Past\ Year', 'end-12months', 0, 0, 2, autoScale)
    createGraph('12m_tx_rate', 'TX_RATE', 'Mbps',
                'Tx\ Rate\ -\ Past\ Year', 'end-12months', 0, 0, 2, autoScale)
    #createGraph('12m_rx_mcs', 'RX_MCS', 'Index',
    #            'Rx\ MCS\ -\ Past\ Year', 'end-12months', 0, 0, 2, autoScale)
    #createGraph('12m_tx_mcs', 'TX_MCS', 'Index',
    #            'Tx\ MCS\ -\ Past\ Year', 'end-12months', 0, 0, 2, autoScale)
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
            print "Usage: %s [-d] [-v] [-pt seconds] [-u url}" % cmd_name[-1]
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
    # last time the rrdtool database updated
    lastDatabaseUpdateTime = -1

    ## Get command line arguments.
    getCLarguments()

    requestIntervalSeconds = dataRequestInterval * 60 # convert to seconds

    chartUpdateInterval = dataRequestInterval # get charts when updating database

    ## Exit with error if rrdtool database does not exist.
    if not os.path.exists(_RRD_FILE):
        print 'rrdtool database does not exist\n' \
              'use createRadmonRrd script to ' \
              'create rrdtool database\n'
        exit(1)
 
    ## main loop
    while True:

        currentTime = time.time() # get current time in seconds

        # Every web update interval request data from the aredn
        # node and process the received data.
        if currentTime - lastDataRequestTime > requestIntervalSeconds:
            lastDataRequestTime = currentTime
            ldData = []
            result = True

            # Get the data string from the device.
            sData = getArednNodeData()
            # If the first http request fails, try one more time.
            if sData == None:
                time.sleep(5)
                sData = getArednNodeData()
                if sData == None:
                    result = False

            # If successful parse the data.
            if result:
                result = parseNodeData(sData, ldData)
           
            # If parsing successful, convert the data.
            if result:
                result = convertData(ldData)

            # If conversion successful, write data to data files.
            if result:
                result = updateDatabase(ldData)

            if result:
                writeOutputDataFile(sData, ldData)

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
