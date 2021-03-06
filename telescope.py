import astropy.units as u
import glob
import numpy as np
import serial
import sys


from astropy.coordinates import get_sun
from astropy.coordinates import AltAz
from astropy.coordinates import EarthLocation
from astropy.coordinates import SkyCoord
import sys
import logging

from astropy.time import Time
from time import sleep

class Telescope():
    def __init__(self):
        self.telescopeAvailable = True
        sp = serial.Serial()
        sp.port = self.find_port() # Improve this using glob
        sp.baudrate = 9600
        sp.parity = serial.PARITY_NONE
        sp.bytesize = serial.EIGHTBITS
        sp.stopbits = serial.STOPBITS_ONE
        sp.timeout = 0.05 #1.5 to give the hardware handshake time to happen
        sp.xonxoff = False
        sp.rtscts = False
        sp.dtrdsr = False
        sp.open()
        sp.setDTR(0)
        self.sp = sp  

    def find_port(self):
        res = glob.glob('/dev/cu.usbserial-14*')
        if len(res) == 1:
            logging.info("Found telescope on port: {0:s}".format(res[0]))
            return res[0]
        else:
            logging.critical("Couldn't locate usbserial device for communicating with telescope")
            sys.exit(0)

    def send_query(self, qr):
        out = self.send_query2(qr)
        while out is None:
            sleep(0.3)
            logging.warning('Telescope serial command blocked executing command {0:s} - retrying'.format(qr))
            out = self.send_query(qr)
        return out

    def send_query2(self, qr):
        try:
            self.sp.write(str.encode(':'+qr+'#'))
            out = self.sp.readline()
            return out
        except (OSError, serial.serialutil.SerialException, UnboundLocalError):
            return None
        

    def goto(self, sunpos, wait=30):
        ra_str = sunpos.ra.to_string(u.hour, sep=':', precision=0, pad=True)
        dec_str = sunpos.dec.to_string(u.deg, sep=':', precision=2, pad=True)
        logging.info("slewing telescope to RA: {0:s} DEC: {1:s}".format(ra_str, dec_str))
        self.send_query('Sr{0:s}'.format(ra_str))
        sleep(0.5)
        self.send_query('Sd{0:s}'.format(dec_str))
        sleep(0.5)
        self.send_query('MM')
        sleep(wait)
        ra = self.send_query('GR').decode('utf-8').replace('#','')
        dec = self.send_query('GD').decode('utf-8').replace('#','')
        logging.info("Telescope pointing to RA {0:s} DEC: {1:s}".format(ra, dec))
    
    def get_status(self):
        ra = self.send_query('GR').decode('utf-8')[0:-1]
        dec = self.send_query('GD').decode('utf-8')[0:-1]
        orientation = self.send_query('Gm').decode('utf-8')[0:-1]
        velocity = self.send_query('Gv').decode('utf-8')
        coord_str = "{0:s} {1:s}".format(ra, dec)
        if orientation == 'W':
            orientation_str = 'West (morning)'
        elif orientation =='E':
            orientation_str = 'East (afternoon)'
        else:
            orientation_str = 'Unknown'
        if velocity == 'N':
            velocity_str = 'Stationary'
        elif velocity == 'T':
            velocity_str = 'Tracking'
        elif velocity == 'C':
            velocity_str = 'Centering'
        elif velocity == 'S':
            velocity_str = 'Slewing'
        else:
            velocity_str = 'Unknown'
        tnow = Time.now() - 7*u.h
        return {'telescope_coords':coord_str, 
                'telescope_orientation':orientation_str, 
                'telescope_velocity':velocity_str, 
                'telescope_update_time':tnow.iso[0:19]}
    
    def park(self):
        self.send_query('hC')
        return

    def goto_sun(self):
        site = EarthLocation.of_site('lowell')
        frame = AltAz(obstime=Time.now(), location=site)
        sun = get_sun(Time.now())
        self.goto(sun)
 
class FakeTelescope():
    def __init__(self):
        return

    def send_query(self, qr):
        return 
        
    def goto(self, sunpos):
        ra_str = sunpos.ra.to_string(u.hour, sep=':', precision=0, pad=True)
        dec_str = sunpos.dec.to_string(u.deg, sep=':', precision=2, pad=True)
        logging.info("slewing telescope to RA: {0:s} DEC: {1:s}".format(ra_str, dec_str))