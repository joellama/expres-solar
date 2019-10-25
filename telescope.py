import argparse
import json
import numpy as np
import os
import pandas as pd
import pytz
import requests
import socketio
import sys
import time
import warnings

from datetime import datetime

from itertools import chain

import serial

import astropy.units as u

from apscheduler.schedulers.background import BackgroundScheduler
from astropy.coordinates import AltAz
from astropy.coordinates import EarthLocation
from astropy.coordinates import SkyCoord
from astropy.coordinates import get_sun
from astropy.table import Table
from astropy.time import Time

class Telescope():
    def __init__(self):
        sp = serial.Serial()
        sp.port = '/dev/cu.usbserial-14230'
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
        self.log = Table(dtype=[
                       ("ISOT",'S19'),
                       ("MJD", np.float),  
                       ("RA", 'S9'),
                       ("DEC", 'S9'),
                       ("MOUNT_SIDE", 'S1'),
                       ("MODE", "S1")])

 

    def send_query(self, qr):
        self.sp.write(str.encode(':'+qr+'#'))
        out = self.sp.readline()
        return out

    def goto(self, sunpos):
        ra_str = sunpos.ra.to_string(u.hour, sep=':', precision=0, pad=True)
        dec_str = sunpos.dec.to_string(u.deg, sep=':', precision=2, pad=True)
        print("slewing telescope to RA: {0:s} DEC: {1:s}".format(ra_str, dec_str))
        send_ra = self.send_query('Sr{0:s}'.format(ra_str))
        send_dec = self.send_query('Sd{0:s}'.format(dec_str))
        self.send_query('MM')
    
    def get_status(self):
        ra = self.send_query('GR').decode('utf-8')[0:-1]
        dec = self.send_query('GD').decode('utf-8')[0:-1]
        mount_side = self.send_query('Gm').decode('utf-8')[0:-1]
        mode = self.send_query('Gv').decode('utf-8')
        # if mode == 'N':
        #     mode_str = 'Not Tracking'
        # elif mode == 'T':
        #     mode_str = 'Tracking'
        # elif mode == 'C':
        #     mode_str = 'Centering'
        # elif mode == 'S':
        #     mode_str = 'Slewing'
        # else:
        #     mode_str = 'Unknown'
        tnow = Time.now() - 7*u.h
        self.log.add_row([tnow.isot[0:19], tnow.mjd, ra, dec, mount_side, mode])

    def make_log_table(self):
        self.log.remove_rows(np.arange(0, len(self.log), dtype=np.log))


class FakeTelescope():
    def __init__(self):
        return

    def send_query(self, qr):
        return 
        
    def goto(self, sunpos):
        ra_str = sunpos.ra.to_string(u.hour, sep=':', precision=0, pad=True)
        dec_str = sunpos.dec.to_string(u.deg, sep=':', precision=2, pad=True)
        print("slewing telescope to RA: {0:s} DEC: {1:s}".format(ra_str, dec_str))