1.  Create a folder for the writemmory files.
2.  Copy the files writememory.py and ft991.py to the folder.
3.  Use the following commands to make the file executable
        chmod +x writememory.py
4.  An example of a comma delimited spreadsheet has been provided.
    To use the example without actually programming your FT991 run
    the following command
        ./writememory.py -d -v -f example.csv
5.  Using the -d debug option prevents commands from actually being
    written to the FT991.  Using the -v verbose option allows you to
    see the commands that are sent to the FT991.  The -f file option
    allows you to use a custom file name for the settings file.
6.  A LibreOffice spreadsheet template "ft991_memory_settings.ots" has
    been provided to help you create comma delimited settings files.
    Various cells have dropdown list boxes for modes, tones, dcs codes, etc.
    You should use these list boxes for setting those items.  Save the
    spreadsheet in comma delimited format (.csv).
7.  Incorrectly entered modes, codes, tones, etc, will cause to program
    to crash, most likely with a dictionary object, key error.
