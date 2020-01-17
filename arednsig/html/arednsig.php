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
 done - Convert dates to  epoch time
 done - Rrdtool - get first in time and last in time
 From above validate begin and end dates
 Rrdtool - create charts of time period

 use $output = shell_exec($cmd); to execute rrdtool commands

*/
# round robin database file
$_RRD_FILE = "/home/pi/database/arednsigData.rrd";
# charts html directory
$_GRAPH_DIRECTORY = "/home/pi/public_html/arednsig/dynamic/";
# standard chart width in pixels
$_GRAPH_WIDTH = 600;
# standard chart height in pixels
$_GRAPH_HEIGHT = 150;
# debug mode
$_DEBUG = false;

error_reporting(E_ALL);

# Get user supplied chart begin and end dates.

$beginDate = $_POST["beginDate"];
$endDate =  $_POST["endDate"];

$cmd = sprintf("rrdtool first %s --rraindex 1",$_RRD_FILE);
$firstDP = shell_exec($cmd);

$cmd = sprintf("rrdtool last %s", $_RRD_FILE);
$lastDP = shell_exec($cmd);

$beginDateEp = strtotime($beginDate);
$endDateEp = strtotime($endDate);

# data entry validation and error checking

if ($beginDateEp > $endDateEp) {
    echo "<p id=\"errorMsg\">" .
         "End date must be after begin date.</p>";
} elseif ($beginDateEp < $firstDP || $endDateEp > $lastDP) {
    echo "<p id=\"errorMsg\">" .
          "Date range must be between " .
          date('m / d / Y', $firstDP) . " and " . 
          date('m / d / Y', $lastDP) . ".</p>";
} else {
    createChart('custom_signal', 'S', 'dBm', 
                'RSSI', $beginDateEp, $endDateEp,
                 0, 0, 2, false);
    createChart('custom_snr', 'SNR', 'dBm', 
                'S/N', $beginDateEp, $endDateEp,
                 0, 0, 2, false);
    if ($_DEBUG) {
        echo "<p>Date range: " . $beginDateEp . " thru " .
              $endDateEp . "</p>";
    }

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
    global $_DEBUG, $_GRAPH_DIRECTORY, $_GRAPH_WIDTH,
           $_GRAPH_HEIGHT, $_RRD_FILE;

    $chartPath = $_GRAPH_DIRECTORY . $chartFile . ".png";

    # Format the rrdtool chart command.

    # Set chart start time, height, and width.
    $cmdfmt = "rrdtool graph %s -a PNG -s %s -e %s -w %s -h %s ";
    $cmd = sprintf($cmdfmt, $chartPath, $begin, $end, $_GRAPH_WIDTH,
                   $_GRAPH_HEIGHT);
    $cmdfmt = "-l %s -u %s -r ";
    if ($lower < $upper) {
        $cmd .= sprintf($cmdfmt, $lower, $upper);
    } elseif ($autoScale) {
        $cmd .= "-A ";
    }
    $cmd .= "-Y ";

    # Set the chart ordinate label and chart title. 
    $cmdfmt = "-v %s -t %s ";
    $cmd .= sprintf($cmdfmt, $label, $title);
   
    # Show the data, or a moving average trend line over
    # the data, or both.
    $trendWindow = floor(($end - $begin) / 12);
    
    $cmdfmt = "DEF:dSeries=%s:%s:LAST ";
    $cmd .= sprintf($cmdfmt, $_RRD_FILE, $dataItem);

    if ($addTrend == 0) {
        $cmd .= "LINE1:dSeries#0400ff ";
    } elseif ($addTrend == 1) {
        $cmdfmt = "CDEF:smoothed=dSeries,%s,TREND LINE3:smoothed#ff0000 ";
        $cmd .= sprintf($cmdfmt, $trendWindow);
    } elseif ($addTrend == 2) {
        $cmd .= "LINE1:dSeries#0400ff ";
        $cmdfmt = "CDEF:smoothed=dSeries,%s,TREND LINE3:smoothed#ff0000 ";
        $cmd .=  sprintf($cmdfmt, $trendWindow);
    }
     
    if ($_DEBUG) {
        echo "<p>chart command:<br>" . $cmd . "</p>";
    }

    $result = shell_exec($cmd . "2>&1");
    if ($_DEBUG == true) {
        echo "<p>result:<br>" . $result . "</p>";
    }
}

?>

</body>
</html>
