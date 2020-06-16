import astropy.units as u
import glob
import numpy as np
import serial

import sys

from astropy.time import Time
from time import sleep

class Telescope():
    def __init__(self):
        sp = serial.Serial()
        sp.port = self.find_port() # Improve this using glob
        sp.baudrate = 9600
        sp.parity = serial.PARITY_NONE
        sp.bytesize = serial.EIGHTBITS
        sp.stopbits = serial.STOPBITS_ONE
        sp.timeout = 1 #1.5 to give the hardware handshake time to happen
        sp.xonxoff = False
        sp.rtscts = False
        sp.dtrdsr = False
        sp.open()
        sp.setDTR(0)
        self.sp = sp  

    def find_port(self):
        res = glob.glob('/dev/cu.usbserial-14*')
        if len(res) == 1:
            print("Found telescope on port: {0:s}".format(res[0]))
            return res[0]
        else:
            print("Couldn't locate usbserial device for communicating with telescope")
            sys.exit(0)

    def send_query(self, qr):
        self.sp.write(str.encode(':'+qr+'#'))
        sleep(0.5)
        out = self.sp.readline()
        return out

    def goto(self, sunpos):
        ra_str = sunpos.ra.to_string(u.hour, sep=':', precision=0, pad=True)
        dec_str = sunpos.dec.to_string(u.deg, sep=':', precision=2, pad=True)
        print("slewing telescope to RA: {0:s} DEC: {1:s}".format(ra_str, dec_str))
        self.send_query('Sr{0:s}'.format(ra_str))
        sleep(0.5)
        self.send_query('Sd{0:s}'.format(dec_str))
        sleep(0.5)
        self.send_query('MM')
        sleep(30)
        ra = self.send_query('GR').decode('utf-8').replace('#','')
        dec = self.send_query('GD').decode('utf-8').replace('#','')
        print("Telescope pointing to RA {0:s} DEC: {1:s}".format(ra, dec))
    
    def get_status(self):
        ra = self.send_query('GR').decode('utf-8')[0:-1]
        dec = self.send_query('GD').decode('utf-8')[0:-1]
        mount_side = self.send_query('Gm').decode('utf-8')[0:-1]
        mode = self.send_query('Gv').decode('utf-8')
        # if mode == 'N':
        #     mode_str = 'Not Tracking'
        # elif mode == 'T':
        #     mode_str = 'Tracking'  15:43:14 DEC: -19:43:33.47
        # elif mode == 'C':
        #     mode_str = 'Centering'
        # elif mode == 'S':
        #     mode_str = 'Slewing'
        # else:
        #     mode_str = 'Unknown'
        tnow = Time.now() - 7*u.h
 
class FakeTelescope():
    def __init__(self):
        return

    def send_query(self, qr):
        return 
        
    def goto(self, sunpos):
        ra_str = sunpos.ra.to_string(u.hour, sep=':', precision=0, pad=True)
        dec_str = sunpos.dec.to_string(u.deg, sep=':', precision=2, pad=True)
        print("slewing telescope to RA: {0:s} DEC: {1:s}".format(ra_str, dec_str))