import json
import numpy as np
import os
import pandas as pd
import pytz
import requests
import socketio
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
 

class guider():
    def __init__(self): 
        sp = serial.Serial()
        sp.port = '/dev/cu.usbserial-A105ADUQ' 
        sp.baudrate = 38400
        sp.parity = serial.PARITY_NONE
        sp.bytesize = serial.EIGHTBITS
        sp.stopbits = serial.STOPBITS_ONE
        sp.timeout = 1 #1.5 to give the hardware handshake time to happen
        sp.xonxoff = True
        sp.rtscts = True
        sp.dtrdsr = True
        sp.open()
        sp.setDTR(0)
        self.sp = sp
        self.log = Table(dtype=[
                       ("ISOT",'S19'),
                       ("MJD", np.float),  
                       ('ECHOCOMMAND','S4'), 
                       ('MODE', np.int),
                       ('VOLUME', np.int),
                       ('FINDERSOUND', np.int),
                       ('X_EXP', np.float),
                       ('Y_EXP', np.float),
                       ('X_RA_POS', np.float),
                       ('Y_RA_POS', np.float),
                       ('X_RA_OPT_OFF', np.float),
                       ('Y_RA_OPT_OFF', np.float),
                       ('X_RA_MECH_OFF', np.float),
                       ('Y_RA_MECH_OFF', np.float),
                       ('XCORR', np.float),
                       ('YCORR', np.float),
                       ('AGGRESS', np.int),
                       ('CORR_EST', np.float),
                       ('X_SCALE', np.float),
                       ('Y_SCALE', np.float),
                       ('THETA_X', np.float),
                       ('Y_DIR', np.int),
                       ('FW_VER', np.float),
                       ('RELAY_STATE', np.float),
                       ('SUN_VIS', np.float),
                       ('CAL_STATE', np.float), 
                       ('MESSAGE', '<S20'),
                       ('CHECKSUM', np.long)
                       ])

    def send_query(self, qr):
        self.sp.write(str.encode(qr))
        out = self.sp.readline()
        l = [[Time.now().isot[0:19]], [Time.now().mjd], out.decode().replace('\r\n','').split(',')] 
        self.log.add_row(list(chain.from_iterable(l)))

class telescope():
    def __init__(self):
        sp = serial.Serial()
        sp.port = '/dev/cu.usbserial'
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

    def send_query(self, qr):
        self.sp.write(str.encode(':'+qr+'#'))
        out = self.sp.readline()
        print(out)

    def goto(self, sunpos):
        ra_str = sunpos.ra.to_string(u.hour, sep=':', precision=0, pad=True)
        dec_str = sunpos.dec.to_string(u.deg, sep=':', precision=2, pad=True)
        print("slewing telescope to RA: {0:s} DEC: {1:s}".format(ra_str, dec_str))
        send_ra = self.send_query('Sr{0:s}'.format(ra_str))
        send_dec = self.send_query('Sd{0:s}'.format(dec_str))
        self.send_query('MM')
 

class expres_solar():
    def __init__(self):
        self.sio = socketio.Client()
        self.sio.connect('http://localhost:8080')
        self.telescope = telescope()
        self.guider = guider()
        self.site = EarthLocation.of_site('dct')
        self.tz = pytz.timezone('US/Arizona')
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.scheduler.add_job(self.plan_the_day, 'cron', hour=1, minute=0, replace_existing=True)
        self.just_initizalized = True
        self.plan_the_day()

    def get_time(self):
        self.iso = Time.now().iso[0:19]
        self.mjd = Time.now().mjd
        self.utdate = '{0:d}{1:d}{2:d}'.format(Time.now().datetime.year, Time.now().datetime.month, Time.now().datetime.day)
        self.sio.emit('update', {'iso':'{0:s}'.format(self.iso),
                                 'mjd':'{0:.5f}'.format(self.mjd),
                                 'utdate': self.utdate
                                 })
        return
     
    def get_sun_coords(self):
        frame = AltAz(obstime=Time.now(), location=self.site)
        sun = get_sun(Time.now())
        return sun, frame

    def get_sun_for_whole_day(self):
        tnow = datetime.now().date()
        today = datetime(tnow.year, tnow.month, tnow.day, 0, 0, 0, tzinfo=self.tz)
        tomorrow = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=self.tz)
        time_arr = pd.date_range(start=today, end=tomorrow, freq='1min')
        frame = AltAz(obstime=time_arr, location=self.site)
        sun = get_sun(Time(time_arr))
        self.sunpos = pd.DataFrame()
        self.sunpos['ISO_AZ'] = time_arr.strftime("%Y-%m-%dT%H:%M:%S")
        self.sunpos['ISO_UTC'] = [x.isot[0:19] for x in Time(time_arr)]
        self.sunpos['MJD'] = [x.mjd for x in Time(time_arr)]
        self.sunpos['RA'] = sun.ra.value
        self.sunpos['RA_STR'] = sun.ra.to_string(u.hour, sep=':', precision=0, pad=True)
        self.sunpos['DEC_STR'] = sun.dec.to_string(u.deg, sep=':', precision=2, pad=True)
        self.sunpos['Az'] = sun.transform_to(frame).az.value
        self.sunpos['Alt'] = sun.transform_to(frame).alt.value
        self.sio.emit('sunPlot', self.sunpos[['ISO_AZ','Alt']].to_json(orient='records'))


    def plan_the_day(self): # This gets run at startup and also every day at 1am. 
        self.get_time()
        self.get_weather()      
        self.get_sun_for_whole_day()
        self.sun_up = self.sunpos.query('Alt > 43.2').iloc[0]
        self.sun_down = self.sunpos.query('Alt > 43.2').iloc[-1]
        self.meridian_flip = self.sunpos.iloc[self.sunpos['Alt'].idxmax() + 5] # Go 5 minutes past just to ensure meridian flip
        # self.sio.emit('update', {'sun_up': '{0:s}'.format(self.sun_up['ISO_AZ'][11:-3]),
        #                          'sun_down': '{0:s}'.format(self.sun_down['ISO_AZ'][11:-3]),
        #                          'meridian_flip': '{0:s}'.format(self.meridian_flip['ISO_AZ'][11:-3])})
        print('Sun up time: {0:s} ({1:.6f})'.format(self.sun_up['ISO_AZ'],self.sun_up['MJD'])
        print('Meridian flip time: {0:s} ({1:.6f})'.format(self.meridian_flip['ISO_AZ'],self.meridian_flip['MJD'])
        print('Sun down time: {0:s} ({1:.6f})'.format(self.sun_down['ISO_AZ'],self.sun_down['MJD'])
        self.sio.emit('update', {'sunup': '{0:s} '.format(self.sun_up['ISO_AZ']),
                                 'sundown': '{0:s}'.format(self.sun_down['ISO_AZ']),
                                 'merflip': '{0:s}'.format(self.meridian_flip['ISO_AZ'])
                                 })
        if not self.just_initizalized:
            self.scheduler.add_job(self.morning, 'date', run_date=Time(self.sun_up['ISO_AZ']).datetime, 
                                    replace_existing=True)
            self.scheduler.add_job(self.afternoon, 'date', run_date=Time(self.meridian_flip['ISO_AZ']).datetime, 
                                    replace_existing=True)
            self.scheduler.add_job(self.end_day, 'date', run_date=Time(self.sun_down['ISO_AZ']).datetime, 
                                    replace_existing=True)
        else:
            self.just_initialized = False
            tnow = Time.now().mjd
            print(self.sun_down['MJD'])
            if (tnow > self.sun_up['MJD']) and (tnow <= self.meridian_flip['MJD']):
                self.scheduler.add_job(self.afternoon, 'date', run_date=Time(self.meridian_flip['ISO_AZ']).datetime, 
                                        replace_existing=True)
                self.scheduler.add_job(self.end_day, 'date', run_date=Time(self.sun_down['ISO_AZ']).datetime, 
                                        replace_existing=True)
                self.morning()
            elif (tnow < self.sun_down['MJD']) and (tnow > self.meridian_flip['MJD']):
                self.scheduler.add_job(self.end_day, 'date', run_date=Time(self.sun_down['ISO_AZ']).datetime, 
                                    replace_existing=True)              
                self.afternoon()
            elif (tnow < self.sun_up['MJD']) or (tnow > self.sun_down['MJD']):
              #its night time 
              self.end_day()
            else:
              print("Check your times, this shouldn't be an option")             
 
    def morning(self):
        print('Running Morning script at UTC {0:s}'.format((Time.now() - 7*u.h).isot[0:19]))
        sun, frame = self.get_sun_coords()
        self.telescope.send_query('hW') # Wake up the telescope and start tracking 
        time.sleep(1)
        self.telescope.goto(sun) # Move the telescope 
        time.sleep(30)
        # Start tracking 
        # do all the guider activation here - recalling the AM settings 

    def afternoon(self):
        print('Running Midday script at {0:s}'.format((Time.now() - 7*u.h).isot[0:19]))
        sun, frame = self.get_sun_coords()
        self.telescope.send_query('hN')
        time.sleep(1)
        self.telescope.goto(sun)
        time.sleep(30)
        self.telescope.send_query('hW') # Wake up the telescope and start tracking 
        # Reactivate the guider here - remembering to recall PM 

    def end_day(self):
        print('Running Evening script at {0:s}'.format((Time.now() - 7*u.h).isot[0:19]))
        self.telescope.send_query('hP')
        time.sleep(30)
        self.telescope.send_query('hN') # sleep the telescope
        # Stop guiding 

    def get_temperature(self):
        fh = os.path.join('D:', 'temp_humidity.csv')
        if os.path.exists(fh):
            df = pd.read_csv(fh, delimiter=';', header=17, engine='python')
            self.lostT = df.iloc[-1, 3]
            self.lostRH = df.iloc[-1, 4]
            self.sio.emit('update', {'lostT': '{0:.2f}'.format(self.lostT),
                                     'lostRH': '{0:.2f}'.format(self.lostRH)
                                     })
        else:
            warnings.warn("File {0:s} not found".format(fh))

    def get_weather(self):
        api_key = 'ec05c9f96f55bb12b2ac3b1e332c3112'
        base_url = "http://api.openweathermap.org/data/2.5/weather?"
        complete_url = base_url + "appid=" + api_key + "&lat=34.7444004&lon=-111.4244857"
        response = requests.get(complete_url)
        x = response.json()
        y = x["main"]
        current_temperature = y["temp"]
        weather_description = x["weather"][0]["description"]
        current_pressure = y["pressure"]
        self.weather_description = weather_description
        self.sio.emit("update", {'weather':weather_description})
 

  



x = expres_solar()

@x.sio.on('newWebClient')
def newWebClient(sid):
    print('Sending values to new client')
    x.sio.emit('update', {'utdate':x.utdate,
                          'iso':x.iso,
                          'mjd':'{0:.5f}'.format(x.mjd),
                          'observe':x.observeStatus,
                          "sunRA":'{0:3.3f}'.format(x.sunRA),
                          "sunDec":'{0:3.3f}'.format(x.sunDec),
                          'sunAz':'{0:3.3f}'.format(x.sunAz),
                          'sunAlt':'{0:3.3f}'.format(x.sunAlt),
                          'weather':x.weather_description})

 
 
