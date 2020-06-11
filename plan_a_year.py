import pandas as pd
import pytz
 
import astropy.units as u
import numpy as np 

import sqlalchemy as db

from astropy.coordinates import AltAz
from astropy.coordinates import EarthLocation
from astropy.coordinates import SkyCoord
from astropy.coordinates import get_sun
from astropy.table import Table
from astropy.time import Time
from astropy.time import Time

from datetime import datetime
from datetime import timedelta

 
import sqlalchemy as db


site = EarthLocation.of_site('dct')
tz = pytz.timezone('US/Arizona')  
sun_min_alt = 15     


def get_sun_whole_day(tnow=datetime.now().date()):
    today = datetime(tnow.year, tnow.month, tnow.day, 0, 0, 0, tzinfo=tz)
    tomorrow = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=tz)
    time_arr = pd.date_range(start=today, end=tomorrow, freq='1min')
    frame = AltAz(obstime=time_arr, location=site)
    sun = get_sun(Time(time_arr))
    sunpos = pd.DataFrame()
    sunpos['ISO_AZ'] = time_arr.strftime("%Y-%m-%dT%H:%M:%S")
    sunpos['ISO_UTC'] = [x.isot[0:19] for x in Time(time_arr)]
    sunpos['MJD'] = [x.mjd for x in Time(time_arr)]
    sunpos['RA'] = sun.ra.value
    sunpos['RA_STR'] = sun.ra.to_string(u.hour, sep=':', precision=0, pad=True)
    sunpos['DEC_STR'] = sun.dec.to_string(u.deg, sep=':', precision=2, pad=True)
    sunpos['Az'] = sun.transform_to(frame).az.value
    sunpos['Alt'] = sun.transform_to(frame).alt.value
    return sunpos

def plan_day(tnow=datetime.now().date()):
    sunpos = get_sun_whole_day(tnow=tnow)
    sun_up = sunpos.query('Alt > {0:f}'.format(sun_min_alt)).iloc[0]
    sun_down = sunpos.query('Alt > {0:f}'.format(sun_min_alt)).iloc[-1]
    med_flip = sunpos.iloc[sunpos['Alt'].idxmax() + 5]
    return {'sun_up':sun_up, 'med_flip':med_flip, 'sun_down':sun_down}


if __name__=='__main__':
    # Choose 2020 since it's a leap year - 366 days in the year 
    year_array = [Time('2020-01-01').datetime + timedelta(x) for x in range(366)]
    sun_up = []
    sun_down = []
    med_flip = []
    doy = []
    for t in year_array:
        print(Time(t).iso[0:10])
        sun = plan_day(t)
        doy.append(t.timetuple().tm_yday)
        sun_up.append(sun['sun_up']['ISO_AZ'][11:19])
        med_flip.append(sun['med_flip']['ISO_AZ'][11:19])
        sun_down.append(sun['sun_down']['ISO_AZ'][11:19])
    df = pd.DataFrame({'doy':doy, 'sun_up':sun_up, 'med_flip':med_flip, 
                       'sun_down':sun_down, 'min_alt':np.zeros_like(doy) + sun_min_alt})
    df.to_csv('day_plan.csv', index=False)