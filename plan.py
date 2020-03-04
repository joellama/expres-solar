import pandas as pd
import pytz
 

import astropy.units as u

import sqlalchemy as db

from astropy.coordinates import AltAz
from astropy.coordinates import EarthLocation
from astropy.coordinates import SkyCoord
from astropy.coordinates import get_sun
from astropy.table import Table
from astropy.time import Time
from astropy.time import Time

import numpy as np 

from datetime import datetime


class expres_solar_planner():
    def __init__(self):
        from astropy.utils import iers
        iers.IERS_A_URL = 'https://datacenter.iers.org/data/9/finals2000A.all'
        self.site = EarthLocation.of_site('dct')
        self.tz = pytz.timezone('US/Arizona')  
        self.sun_min_alt = 15      

    def get_time(self):
        self.iso = Time.now().iso[0:19]
        self.mjd = Time.now().mjd
        self.utdate = '{0:04d}{1:02d}{2:02d}'.format(Time.now().datetime.year, Time.now().datetime.month, Time.now().datetime.day)

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

    def convert_to_datetime(self, t):
        return datetime.now().replace(hour=np.long(t[0:2]), minute=np.long(t[3:5]), 
                                      second=0, microsecond=0)

    def plan_the_day(self):
        tnow = datetime.now().date()
        doy = tnow.timetuple().tm_yday
        df = pd.read_csv('day_plan.csv')
        qr = df.query('doy == {0:d}'.format(doy))
        print("Found {0:d} entries for DOY: {1:d}".format(len(qr), doy))
        if len(qr) == 1:
            self.sun_up = Time(self.convert_to_datetime(qr['sun_up'].values[0]))
            self.meridian_flip = Time(self.convert_to_datetime(qr['med_flip'].values[0]))
            self.sun_down = Time(self.convert_to_datetime(qr['sun_down'].values[0]))
            self.utdate = '{0:04d}{1:02d}{2:02d}'.format(tnow.year, tnow.month, tnow.day)    
        else:
            self.get_sun_for_whole_day()
            self.sun_up = self.sunpos.query('Alt > {0:f}'.format(self.sun_min_alt)).iloc[0]
            self.sun_down = self.sunpos.query('Alt > {0:f}'.format(self.sun_min_alt)).iloc[-1]
            self.meridian_flip = self.sunpos.iloc[self.sunpos['Alt'].idxmax() + 5]      
            self.utdate = '{0:04d}{1:02d}{2:02d}'.format(tnow.year, tnow.month, tnow.day)     
            engine = db.create_engine("mysql+pymysql://solar:4rp%V5zQgiXEecRRv@10.10.115.149:3307/solar")
            metadata = db.MetaData(bind=engine)
            planTable = db.Table('plan', metadata, autoload=True)
            connection = engine.connect()
            # Check if today already exists 
            qr = planTable.select().where(planTable.c.DATE==self.utdate)
            res = connection.execute(qr)
            if (res.rowcount == 0):
                connection.execute(planTable.insert().values(DATE=self.utdate, 
                                                        SUNUP=Time(self.sun_up['ISO_AZ']).datetime,
                                                        MEDFLIP=Time(self.meridian_flip['ISO_AZ']).datetime,
                                                        SUNDOWN=Time(self.sun_down['ISO_AZ']).datetime),
                                                        MINALT=self.sun_min_alt)
            connection.close()      

