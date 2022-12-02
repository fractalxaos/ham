#!/usr/bin/python

# courtsey ruler for editing script - 80 characters max line length
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

import telnetlib

_DEFAULT_HOST = '{your APRS-IS server hostname}'
_DEFAULT_PORT = '{your APRS-IS message port}'
_DEFAULT_SERVER = '{your APRS-IS server name}'

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
          text_message - text message to be sent to the provided phone number
        Returns: True if successful, False otherwise
        """
        # Establish network connection to APRS-IS server.
        tn = telnetlib.Telnet(self.host, self.port)
        tn.read_until('# aprsc 2.1.8-gf8824e8')

        # Login and verify passcode accepted.
        tn.write('user ' + self.callsign + ' pass ' + self.passcode + '\n')
        response = tn.read_until(self.server)
        if self.debug:
            print('response: ' + response[2:])
        if not response.find('verified'):
            print('smsalert error: unverified user')
            del tn
            return False

        # Format and send SMS message to SMS gateway.
        cmd = '%s>%s::SMSGTE:@%s %s' % \
          (self.callsign, self.server, phone_number, text_message)
        if self.debug:
            print('cmd: ' + cmd)
        tn.write(cmd + '\n')
        del tn
        return True
    ## end def
## end class

def test_smsalert():
    # Initialize a telnet instance.  Default host, port, and server
    # automatically defined if not included in function call.
    sm = smsalert('{your callsign}', '{your passcode}', debug=True)

    # Send a text message to a phone number.
    sm.sendSMS('{your phone number}', 'Test message send from smsalert.py')
## end def

if __name__ == '__main__':
    test_smsalert()
