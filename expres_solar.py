import argparse
import json
import numpy as np
import os
import pandas as pd
import pytz
import requests
import signal
import socketio
import sys
import time
import warnings

from datetime import datetime

from itertools import chain
from time import strptime
import serial

import astropy.units as u

from apscheduler.schedulers.background import BackgroundScheduler
from astropy.coordinates import AltAz
from astropy.coordinates import EarthLocation
from astropy.coordinates import SkyCoord
from astropy.coordinates import get_sun
from astropy.table import Table
from astropy.time import Time
 

from guider import FakeGuider
from guider import Guider

from telescope import FakeTelescope
from telescope import Telescope

import sqlite3

from astropy.utils import iers

iers.IERS_A_URL = 'https://datacenter.iers.org/data/9/finals2000A.all'

class expres_solar():
    def __init__(self, sim_guider=False, sim_telescope=False, 
                       data_root='./data', sun_min_alt=15,
                       use_scheduler=True):
        self.sio = socketio.Client()
        self.use_scheduler = use_scheduler
        self.sio.connect('http://localhost:8081')
        self.data_root = data_root
        # self.telescope = telescope()
        if not sim_guider:
          print('using real guider')
          self.guider = Guider()
        else:
          print('using simulated guider')
          self.guider = FakeGuider()
        if not sim_telescope:
          print('using real Telescope')
          self.telescope = Telescope()
          _ = self.telescope.send_query('GC')
          print('Mount Date: {0:s}'.format(_.decode('utf-8')))
          _ = self.telescope.send_query('GL')
          print('Mount Time (UTC): {0:s}'.format(_.decode('utf-8')))
        else:
          print('using simulated telescope')
          self.telescope = FakeTelescope()          
        self.site = EarthLocation.of_site('dct')
        self.tz = pytz.timezone('US/Arizona')
        if self.use_scheduler:
          self.scheduler = BackgroundScheduler()
          self.scheduler.start()
          self.scheduler.add_job(self.plan_the_day, 'cron', hour=1, minute=0, replace_existing=True)
          self.scheduler.add_job(self.update_web_suncoords, 'interval', seconds=30, replace_existing=True)
          self.scheduler.add_job(self.update_guider_status, 'interval', seconds=10, replace_existing=True, id='update_guider')
          self.scheduler.add_job(self.update_telescope_status, 'interval', seconds=10, replace_existing=True, id='update_telescope')          
        self.just_initizalized = True
        self.sun_min_alt = sun_min_alt # Degrees
        self.guider_counter = 0 # Only update the table every 10 iterations - this should be improved
        self.plan_the_day()

    def get_time(self):
        self.iso = Time.now().iso[0:19]
        self.mjd = Time.now().mjd
        self.utdate = '{0:d}{1:d}{2:d}'.format(Time.now().datetime.year, Time.now().datetime.month, Time.now().datetime.day)
        self.sio.emit('update', {'iso':'{0:s}'.format(self.iso),
                                 'mjd':'{0:.5f}'.format(self.mjd),
                                 'utdate': self.utdate
                                 })
        print('Current MJD: {0:.6f}'.format(self.mjd))
 
     
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
        # self.sio.emit('sunPlot', self.sunpos[['ISO_AZ','Alt']].to_json(orient='records'))


    def plan_the_day(self): # This gets run at startup and also every day at 1am. 
        self.get_time()
        self.data_dir = os.path.join(self.data_root, self.utdate)
        if not os.path.exists(self.data_dir):
            os.mkdir(self.data_dir)        
        self.get_sun_for_whole_day()
        self.sun_up = self.sunpos.query('Alt > {0:f}'.format(self.sun_min_alt)).iloc[0]
        self.sun_down = self.sunpos.query('Alt > {0:f}'.format(self.sun_min_alt)).iloc[-1]
        self.meridian_flip = self.sunpos.iloc[self.sunpos['Alt'].idxmax() + 5] # Go 5 minutes past just to ensure meridian flip
        print_message('Planning the day: {0:s}'.format((Time.now() - 7*u.h).iso[0:19]))
        print('Sun up time: {0:s} ({1:.6f})'.format(self.sun_up['ISO_AZ'],self.sun_up['MJD']))
        print('Meridian flip time: {0:s} ({1:.6f})'.format(self.meridian_flip['ISO_AZ'],self.meridian_flip['MJD']))
        print('Sun down time: {0:s} ({1:.6f})'.format(self.sun_down['ISO_AZ'],self.sun_down['MJD']))
        self.sio.emit('update', {'today': '{0:s}'.format(self.sun_up['ISO_AZ'][0:10]),
                                  'sunup': '{0:s} '.format(self.sun_up['ISO_AZ'][11:-3]),
                                 'sundown': '{0:s}'.format(self.sun_down['ISO_AZ'][11:-3]),
                                 'merflip': '{0:s}'.format(self.meridian_flip['ISO_AZ'][11:-3])
                                 })
        self.sio.emit('clearTables', 'please')
        db_conn = sqlite3.connect(os.path.join(self.data_dir, '{0:s}_log.db'.format(self.utdate)))
        self.sunpos.to_sql(con=db_conn, if_exists='replace', name='sunpos')
        c = db_conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS "guider" (
                        "ISOT" TEXT,
                        "MJD" REAL,
                        "ECHOCOMMAND" TEXT,
                        "MODE" INTEGER,
                        "X_EXP" REAL,
                        "Y_EXP" REAL,
                        "X_RA_POS" INTEGER,
                        "Y_RA_POS" INTEGER,
                        "X_RA_OPT_OFF" INTEGER,
                        "Y_RA_OPT_OFF" INTEGER,
                        "X_RA_MECH_OFF" INTEGER,
                        "Y_RA_MECH_OFF" INTEGER,
                        "XCORR" REAL,
                        "YCORR" REAL,
                        "AGGRESS" INTEGER,
                        "CORR_EST" REAL,
                        "X_SCALE" REAL,
                        "Y_SCALE" REAL,
                        "THETA_X" INEGER,
                        "Y_DIR" INTEGER,
                        "FW_VER" REAL,
                        "RELAY_STATE" INTEGER,
                        "SUN_VIS" INTEGER,
                        "CAL_STATE" INTEGER,
                        "MESSAGE" TEXT,
                        "CHECKSUM" INTEGER
                      )""")
        c.execute("""CREATE TABLE IF NOT EXISTS "telescope" ( 
                        "ISOT" TEXT,
                        "MJD" REAL,
                        "RA" TEXT, 
                        "DEC" TEXT,
                        "MOUNT_SIDE" TEXT,
                        "MODE" TEXT
                      )""")                        
        db_conn.commit()
        db_conn.close()        
        if not self.just_initizalized and self.use_scheduler:
            print_message('Running the initializer')
            self.scheduler.add_job(self.morning, 'date', run_date=Time(self.sun_up['ISO_AZ']).datetime,  replace_existing=True)
            self.scheduler.add_job(self.afternoon, 'date', run_date=Time(self.meridian_flip['ISO_AZ']).datetime,  replace_existing=True)
            self.scheduler.add_job(self.end_day, 'date', run_date=Time(self.sun_down['ISO_AZ']).datetime,  replace_existing=True)
        else:
            # This is the startup scenario. We don't know what time of day this was run so, cycle through the various scenarios
            self.just_initialized = False 
            tnow = Time.now().mjd
            if (tnow > self.sun_up['MJD']) and (tnow <= self.meridian_flip['MJD']) and self.use_scheduler:
                # It's the morning and we should be observing. Schedule the afternoon and evening too. 
                self.scheduler.add_job(self.afternoon, 'date', run_date=Time(self.meridian_flip['ISO_AZ']).datetime, 
                                        replace_existing=True)
                self.scheduler.add_job(self.end_day, 'date', run_date=Time(self.sun_down['ISO_AZ']).datetime, 
                                        replace_existing=True)
                self.morning()
            elif (tnow < self.sun_down['MJD']) and (tnow > self.meridian_flip['MJD']):
                # It's the afternoon, schedule the end of day.  
                self.scheduler.add_job(self.end_day, 'date', run_date=Time(self.sun_down['ISO_AZ']).datetime, 
                                    replace_existing=True)             
                self.afternoon()
            elif (tnow < self.sun_up['MJD']) or (tnow > self.sun_down['MJD']):
              # It's the evening so we need to make sure we're shut down. 
              # A subtlety here, plan the day gets run at 1am, if we arrive here after that but before morning we get stuck so just schedule everything. 
              self.scheduler.add_job(self.morning, 'date', run_date=Time(self.sun_up['ISO_AZ']).datetime, 
                                      replace_existing=True)
              self.scheduler.add_job(self.afternoon, 'date', run_date=Time(self.meridian_flip['ISO_AZ']).datetime, 
                                      replace_existing=True)
              self.scheduler.add_job(self.end_day, 'date', run_date=Time(self.sun_down['ISO_AZ']).datetime, 
                                      replace_existing=True)
              self.end_day()
            else:
              print("Check your times, this shouldn't be an option")    
        self.sio.emit('update', {'today': '{0:s}'.format(self.sun_up['ISO_AZ'][0:10]),
                            'sunup': '{0:s} '.format(self.sun_up['ISO_AZ'][11:-3]),
                           'sundown': '{0:s}'.format(self.sun_down['ISO_AZ'][11:-3]),
                           'merflip': '{0:s}'.format(self.meridian_flip['ISO_AZ'][11:-3])
                           })
 
    def morning(self):
        print_message('Running morning script: {0:s}'.format((Time.now() - 7*u.h).isot[0:19]))
        sun, frame = self.get_sun_coords()
        # self.telescope.send_query('hW') # Wake up the telescope and start tracking         
        self.telescope.goto(sun) # Move the telescope 
        # self.guider.send_query(']')
        self.center_sun()
        time.sleep(2)
        self.guider.send_query("E")
        time.sleep(2)
        self.guider.send_query("A")
        time.sleep(2)
        self.guider.send_query("X")        
        # Start tracking 
        # do all the guider activation here - recalling the AM settings 
        if self.use_scheduler:
          self.scheduler.add_job(self.update_guider_status, 'interval', seconds=10, replace_existing=True, id='update_guider')
          self.scheduler.add_job(self.update_telescope_status, 'interval', seconds=10, replace_existing=True, id='update_telescope')
    
    def afternoon(self):
        print_message('Running Afternoon script: {0:s}'.format((Time.now() - 7*u.h).isot[0:19]))
        sun, frame = self.get_sun_coords()
        if self.use_scheduler:
          self.scheduler.remove_job('update_guider')
          self.scheduler.remove_job('update_telescope')
        self.telescope.send_query('hN')
        time.sleep(5)
        self.telescope.goto(sun)
        # time.sleep(30)
        self.center_sun()
        self.guider.send_query('E')
        time.sleep(0.5)
        self.guider.send_query("F")
        time.sleep(0.5)
        self.guider.send_query("X") 
        self.telescope.send_query('hW') # Wake up the telescope and start tracking 
        # Reactivate the guider here - remembering to recall PM 
        if self.use_scheduler:
          self.scheduler.add_job(self.update_guider_status, 'interval', seconds=10, 
            replace_existing=True, id='update_guider')
          self.scheduler.add_job(self.update_telescope_status, 'interval', seconds=10, 
            replace_existing=True, id='update_telescope')          

    def end_day(self):
        print_message('Running evening script: {0:s}'.format((Time.now() - 7*u.h).isot[0:19]))
        if self.use_scheduler:
          self.scheduler.remove_job('update_guider')
          self.scheduler.remove_job('update_telescope')
        time.sleep(5)
        self.guider.send_query(']')
        self.telescope.send_query('hC')
        time.sleep(30)
        # time.sleep(120)
        self.telescope.send_query('hN') # sleep the telescope
        if self.use_scheduler:
          self.scheduler.add_job(self.update_guider_status, 'interval', seconds=600, replace_existing=True,
            id='update_guider')
          self.scheduler.add_job(self.update_telescope_status, 'interval', seconds=600, replace_existing=True,
            id='update_telescope')
  
    def center_sun(self, center_px=(68, 60)):
        plate_scale = 0.05*u.deg # Not exact, but close enough
        self.guider.send_query('S')
        xloc = self.guider.log['X_RA_POS'][-1]
        yloc = self.guider.log['Y_RA_POS'][-1]
        xcorr = (xloc - center_px[0])
        ycorr = (yloc - center_px[1])
        ra = self.telescope.send_query('GR').decode("utf-8")[0:-1]
        dec = self.telescope.send_query('GD').decode("utf-8")[0:-1]
        c = SkyCoord('{0:s} {1:s}'.format(ra, dec), 
            unit=(u.hourangle, u.deg))
        cnew = SkyCoord(c.ra + 0*plate_scale, c.dec + ycorr*plate_scale)
        self.telescope.send_query('Sr{0:s}'.format(cnew.ra.to_string(u.hour, sep=':', precision=2, pad=True)))
        self.telescope.send_query('Sd{0:s}'.format(cnew.dec.to_string(u.deg, sep=':', precision=2, pad=True)))
        self.telescope.send_query("MM")
        print_message('Adjusting the Sun image by RA: {0:3.2f} deg, DEC: {1:3.2f} deg'.format((xcorr*plate_scale).value, (ycorr*plate_scale).value), padding=False)
        time.sleep(2)

    def update_web_suncoords(self):
        return
        # sun, frame = self.get_sun_coords()
        # self.sio.emit({'sunalt': '{0:.2f}'.format(sun.transform_to(frame).alt.value)})
        # self.sio.emit('update', {'sunalt': '{0:.2f}'.format(sun.transform_to(frame).alt.value),
        #                           'sunRA': sun.ra.to_string(u.hour, sep=':', precision=0, pad=True),
        #                           'sunDEC': sun.dec.to_string(u.deg, sep=':', precision=2, pad=True)
        #                           })

    def update_telescope_status(self):
        print_message('Updating telescope status: {0:s}'.format((Time.now() - 7*u.h).isot[0:19]), padding=False)
        self.telescope.get_status()
        db_conn = sqlite3.connect(os.path.join(self.data_dir, '{0:s}_log.db'.format(self.utdate)))
        c = db_conn.cursor()
        for_db = self.telescope.log.to_pandas().iloc[-1, :]
        try:
          c.execute("INSERT INTO telescope VALUES (?, ?, ?, ?, ?, ?)", 
              list(for_db))
          db_conn.commit()
        except:
          pass
        db_conn.close()      
        print(for_db['RA'])
        self.sio.emit('update', {'telescope_ra': for_db['RA'].decode('utf-8'), 'telescope_dec': for_db['DEC'].decode('utf-8'), 
              'telescope_orientation':for_db['MOUNT_SIDE'].decode('utf-8'), 'telescope_mode': for_db['MODE'].decode('utf-8')})


    def update_guider_status(self):
        print_message('Updating guider status: {0:s}'.format((Time.now() - 7*u.h).isot[0:19]), padding=False)
        self.guider.send_query('S')
        for_db = convert_cols_from_bytes(self.guider.log.to_pandas())
        col_list = {'ISOT':"TEXT",
                     'MJD':"REAL",
                     'ECHOCOMMAND':"TEXT",
                     'MODE':"INTEGER",
                     'X_EXP':"REAL",
                     'Y_EXP':"REAL",
                     'X_RA_POS':"REAL",
                     'Y_RA_POS':"REAL",
                     'X_RA_OPT_OFF':"REAL",
                     'Y_RA_OPT_OFF':"REAL",
                     'X_RA_MECH_OFF':"REAL",
                     'Y_RA_MECH_OFF':"REAL",
                     'XCORR':"REAL",
                     'YCORR':"REAL",
                     'AGGRESS':"REAL",
                     'CORR_EST':"REAL",
                     'X_SCALE':"REAL",
                     'Y_SCALE':"REAL",
                     'THETA_X':"REAL",
                     'Y_DIR':"REAL",
                     'FW_VER':"TEXT",
                     'RELAY_STATE':"REAL",
                     'SUN_VIS':"REAL",
                     'CAL_STATE':"REAL",
                     'MESSAGE':"TEXT",
                     'CHECKSUM':"INTEGER"}
        db_conn = sqlite3.connect(os.path.join(self.data_dir, '{0:s}_log.db'.format(self.utdate)))
        c = db_conn.cursor()
        try:
          c.execute("INSERT INTO guider VALUES  (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                  (for_db[[x for x in col_list.keys()]].iloc[-1,:]))
          db_conn.commit()
        except:
          pass
        db_conn.close()         

        self.sio.emit('sunIntensity', float(np.log2(23.4 / (( for_db.loc[0, 'Y_EXP'] * 1.017) + 23.4))))
        self.guider_counter += 1
        if self.guider_counter == 10:
            self.sio.emit('guiderUpdate', {'mode':int(for_db.loc[0, 'MODE']), 
                                       'sun_vis':int(for_db.loc[0, 'Y_EXP'] / 327.67), 
                                       'XCORR':int(for_db.loc[0,'XCORR']), 
                                       'YCORR':int(for_db.loc[0,'YCORR'])})
            self.guider_counter = 0


def convert_cols_from_bytes(df):
  str_df = df.select_dtypes([np.object])
  str_df = str_df.stack().str.decode('utf-8').unstack()
  for col in str_df:
    df[col] = str_df[col]
  return df

def signal_handler(signal, frame):
  print('exiting code')
  # Park telescope here
  # x.end_day() 
  # x.scheduler.stop(wait=False)
  sys.exit(0)

def print_message(msg, padding=True):
  if padding:
    print(''.join(np.repeat('-', 11 + len(msg) + 11)))
  print('{0:s} {1:s} {0:s}'.format(''.join(np.repeat('-', 10)), msg))
  if padding:
    print(''.join(np.repeat('-', 11 + len(msg) + 11)))

if __name__ == "__main__":
  
  parser = argparse.ArgumentParser(description='Use real of simulated guider')
  parser.add_argument('--sim_guider', dest='sim_guider', default=False, 
                                      action='store_true',
                                      help='If called use a simulated guider')
  parser.add_argument('--sim_telescope', dest='sim_telescope', default=False, 
                                      action='store_true',
                                      help='If called use a simulated telescope')  
  args = parser.parse_args()
  x = expres_solar(sim_guider=args.sim_guider, sim_telescope=args.sim_telescope)
  signal.signal(signal.SIGINT, signal_handler)



@x.sio.on('newWebClient')
def newWebClient(sid):
    print('Sending values to new client')
    sun, frame = x.get_sun_coords()
    x.sio.emit('update', {'sunup': '{0:s} '.format(x.sun_up['ISO_AZ'][11:-3]),
                                 'sundown': '{0:s}'.format(x.sun_down['ISO_AZ'][11:-3]),
                                 'merflip': '{0:s}'.format(x.meridian_flip['ISO_AZ'][11:-3]),
                                 'today': '{0:s}'.format(x.sun_up['ISO_AZ'][0:10]),
                                 'sunalt': '{0:.2f}'.format(sun.transform_to(frame).alt.value),
                                'sunRA': sun.ra.to_string(u.hour, sep=':', precision=0, pad=True),
                                'sunDEC': sun.dec.to_string(u.deg, sep=':', precision=2, pad=True)
                                })


