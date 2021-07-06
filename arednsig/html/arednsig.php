<html>
<!-- Courtsey ruler
12345678901234567890123456789012345678901234567890123456789012345678901234567890
-->
<head>
<style>
p {
    font: 14px ariel, sans serif;
}
#errorMsg {
    font:bold 18px arial,sans-serif;
    color:red;
    text-align:center;
}
.chartContainer {
    padding: 2px;
}
img.chart {
    width:100%;
}
</style>
</head>
<body>

<?php
/*
 Script: arednsig.php

 Description: This scripts generates on the server charts showing
 signal data spanning the period supplied by the user.  The script
 does the following:
    - converts user supplied dates to  epoch time
    - gets the times of the first and last data point in the round
      robin database (RRD)
    - from above validates user supplied begin and end dates
    - creates charts of the specified period

 Copyright 2020 Jeff Owrey
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see http://www.gnu.org/license.

 Revision History
   * v20 released 18 Jan 2020 by J L Owrey; first release
*/

# Define global constants

# round robin database file
define("_RRD_FILE", str_replace("public_html/arednsig/arednsig.php",
                                "database/arednsigData.rrd",
                                $_SERVER["SCRIPT_FILENAME"]));
# charts html directory
define("_CHART_DIRECTORY", str_replace("arednsig.php",
                                       "dynamic/",
                                       $_SERVER["SCRIPT_FILENAME"]));
# standard chart width in pixels
define("_CHART_WIDTH", 600);
# standard chart height in pixels
define("_CHART_HEIGHT", 150);
# debug mode
define("_DEBUG", false);

# Set error handling modes.
error_reporting(E_ALL);

# Get user supplied chart begin and end dates.
$beginDate = $_POST["beginDate"];
$endDate =  $_POST["endDate"];

# Convert the user supplied dates to epoch time stamps.
$beginDateEp = strtotime($beginDate);
$endDateEp = strtotime($endDate);

# Get the time stamp of the earliest data point in the RRD file.
$cmd = sprintf("rrdtool first %s --rraindex 1", _RRD_FILE);
$firstDP = shell_exec($cmd);

# Get the time stamp of the latest data point in the RRD file.
$cmd = sprintf("rrdtool last %s", _RRD_FILE);
$lastDP = shell_exec($cmd);

# Determine validity of user supplied dates.  User supplied begin
# date must be less than user supplied end date.  Furthermore both
# dates must be within the range of dates stored in the RRD.
if ($beginDateEp > $endDateEp) {
    echo "<p id=\"errorMsg\">" .
         "End date must be after begin date.</p>";
} elseif ($beginDateEp < $firstDP || $endDateEp > $lastDP) {
    echo "<p id=\"errorMsg\">" .
          "Date range must be between " .
          date('m / d / Y', $firstDP) . " and " . 
          date('m / d / Y', $lastDP) . ".</p>";
} else {
    # Generate charts from validated user supplied dates.
    if (_DEBUG) {
        echo "<p>Date range: " . $beginDateEp . " thru " .
              $endDateEp . "</p>";
    }
    createChart('custom_signal', 'S', 'dBm', 
                'RSSI', $beginDateEp, $endDateEp,
                 0, 0, 2, false);
    createChart('custom_snr', 'SNR', 'dBm', 
                'S/N', $beginDateEp, $endDateEp,
                 0, 0, 2, false);
    # Send html commands to client browser.
    echo "<div class=\"chartContainer\">" .
         "<img class=\"chart\" src=\"dynamic/custom_signal.png\">" .
         "</div>";
    echo "<div class=\"chartContainer\">" .
         "<img class=\"chart\" src=\"dynamic/custom_snr.png\">" .
         "</div>";
}

function createChart($chartFile, $dataItem, $label, $title, $begin,
                     $end, $lower, $upper, $addTrend, $autoScale) {
    /*
    Uses rrdtool to create a chart of specified aredn node data item.
    Parameters:
       fileName - name of the created chart file
       dataItem - data item to be charted
       label - string containing a label for the item to be charted
       title - string containing a title for the chart
       begin - beginning time of the chart data
       end   - ending time of the data to be charted
       lower - lower bound for chart ordinate #NOT USED
       upper - upper bound for chart ordinate #NOT USED
       addTrend - 0, show only chart data
                  1, show only a trend line
                  2, show a trend line and the chart data
       autoScale - if True, then use vertical axis auto scaling
           (lower and upper parameters are ignored), otherwise use
           lower and upper parameters to set vertical axis scale
    Returns: True if successful, False otherwise
    */

    # Define path on server to chart files.
    $chartPath = _CHART_DIRECTORY . $chartFile . ".png";

    # Format the rrdtool chart command.

    # Set chart file name, start time, end time, height, and width.
    $cmdfmt = "rrdtool graph %s -a PNG -s %s -e %s -w %s -h %s ";
    $cmd = sprintf($cmdfmt, $chartPath, $begin, $end, _CHART_WIDTH,
                   _CHART_HEIGHT);
    $cmdfmt = "-l %s -u %s -r ";

    # Set upper and lower ordinate bounds.
    if ($lower < $upper) {
        $cmd .= sprintf($cmdfmt, $lower, $upper);
    } elseif ($autoScale) {
        $cmd .= "-A ";
    }
    $cmd .= "-Y ";

    # Set the chart ordinate label and chart title. 
    $cmdfmt = "-v %s -t %s ";
    $cmd .= sprintf($cmdfmt, $label, $title);
   
    # Define moving average window width.
    $trendWindow = floor(($end - $begin) / 12);
        
    # Show the data, or a moving average trend line over
    # the data, or both.
    $cmdfmt = "DEF:dSeries=%s:%s:LAST ";
    $cmd .= sprintf($cmdfmt, _RRD_FILE, $dataItem);
    if ($addTrend == 0) {
        $cmd .= "LINE1:dSeries#0400ff ";
    } elseif ($addTrend == 1) {
        $cmdfmt = "CDEF:smoothed=dSeries,%s,TREND LINE2:smoothed#006600 ";
        $cmd .= sprintf($cmdfmt, $trendWindow);
    } elseif ($addTrend == 2) {
        $cmd .= "LINE1:dSeries#0400ff ";
        $cmdfmt = "CDEF:smoothed=dSeries,%s,TREND LINE2:smoothed#006600 ";
        $cmd .=  sprintf($cmdfmt, $trendWindow);
    }
     
    # Execute the formatted rrdtool command in the shell. The rrdtool
    # command will complete execution before the html image tags get
    # sent to the browser.  This assures that the charts are available
    # when the client browser executes the html code that loads the
    # charts into the document displayed by the client browser.
    if (_DEBUG) {
        echo "<p>chart command:<br>" . $cmd . "</p>";
    }
    $result = shell_exec($cmd . " 2>&1");
    if (_DEBUG) {
        echo "<p>result:<br>" . $result . "</p>";
    }
}

?>

</body>
</html>
