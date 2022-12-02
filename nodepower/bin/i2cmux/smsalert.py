#!/usr/bin/python3
#!/usr/bin/python3
#
# Module: smsalert.py
#
# Description: This module provides a utility for sending SMS text
# messages to an SMS Gateway server.  The gateway server sends the
# text message to the supplied phone number.  This class acts as a
# library module that can be imported into and called from other
# Python programs.
#
# Copyright 2022 Jeff Owrey
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
#   * v10 released 16 March 2022 by J L Owrey; first release
#
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

import telnetlib

_DEFAULT_HOST = 'ai7nc-aprs-is-vm.local.mesh'
_DEFAULT_PORT = '14580'
_DEFAULT_SERVER = 'AI7NC-30'

class smsalert:

    def __init__(self, callsign, passcode, host=_DEFAULT_HOST, \
      port=_DEFAULT_PORT, server=_DEFAULT_SERVER, debug=False):
        """
        Initialize an instance of this class.
        Parameters:
          callsign - amateur radio callsign of user (must be verified)
          passcode - passcode for verified callsign
          host - domain name or IP address of APRS-IS server
          port - port on which the APRS-IS server receives messages
          server - APRS service name
          debug - set equal to True for debug output
        Returns: nothing
        """
        # Initialize class instance variables.
        self.callsign = callsign
        self.passcode = passcode
        self.host = host
        self.port = port
        self.server = server
        self.debug = debug
    ## end def

    def sendSMS(self, phone_number, text_message):
        """
        Sends an SMS text message to the provided phone number.
        Parameters:
          phone_number - phone number to which to send the text message
          text_message - text message to be sent to the provided
          phone number
        Returns: True if successful, False otherwise
        """
        initial_prompt = '# aprsc 2.1.8-gf8824e8'
        login_string = 'user ' + self.callsign + \
                       ' pass ' + self.passcode + '\n'
        login_result = self.server

        # For compatibility with python 2 telnet library, convert
        # utf-8 strings to bytes.
        initial_prompt = initial_prompt.encode()
        login_string = login_string.encode()
        login_result = login_result.encode()

        try:
            # Establish network connection to APRS-IS server. Look for
            tn = telnetlib.Telnet(self.host, self.port)
            tn.read_until(initial_prompt)

            # Login and verify passcode accepted.
            tn.write(login_string)
            response = tn.read_until(login_result)
            response = response.decode() # convert response to utf-8 string
            if self.debug:
                print('sms response: ' + response[0:])
            if not response.find('verified'):
                print('sms error: unverified user')
                del tn
                return False

            # Format and send SMS message to SMS gateway.
            cmd = '%s>%s::SMSGTE:@%s %s\n' % \
              (self.callsign, self.server, phone_number, text_message)
            if self.debug:
                print('sms cmd: ' + cmd)
            tn.write(cmd.encode())
            del tn
            return True
        except Exception as exError:
            print("sms error: %s" % (exError))
            return False
    ## end def
## end class

def test_smsalert():
    import time

    # Initialize a telnet instance.  Default host, port, and server
    # automatically defined if not included in function call.
    sm = smsalert('KA7JLO', '17318', debug=True)

    # Send a text message to a phone number.
    message = 'Python script test message sent via AREDN: msg %d' % time.time()
    sm.sendSMS('5416021314', message)
## end def

if __name__ == '__main__':
    test_smsalert()
