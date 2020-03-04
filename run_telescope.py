import astropy.units as u
import pandas as pd
import pytz
import socketio
import sqlalchemy as db
import numpy as np 
import yaml
import time
from apscheduler.schedulers.background import BackgroundScheduler
from astropy.coordinates import AltAz
from astropy.coordinates import EarthLocation
from astropy.coordinates import SkyCoord
from astropy.coordinates import get_sun
from astropy.table import Table
from astropy.time import Time
from astropy.utils.iers import conf
from datetime import datetime
from plan import expres_solar_planner
from telescope import Telescope
from guider import Guider
from camera import Camera
conf.auto_max_age = None

def timeSeconds(t):
    tnow = t.datetime
    midnight = tnow.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds = (tnow - midnight).seconds
    return seconds


class expres_solar():
    def __init__(self):
        self.site = EarthLocation.of_site('dct')
        self.tz = pytz.timezone('US/Arizona')     
        self.guider = Guider()   
        self.camera = Camera()
        self.planner = expres_solar_planner()
        self.sio = socketio.Client()    
        self.sio.connect('http://localhost:8081')
        self.telescope = Telescope()
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.scheduler.add_job(self.getDayPlan, 'cron', hour=1, minute=0, replace_existing=True)        
        
        self.getDayPlan() # Also need to run this on the first run through 
        t = Time(datetime.now())
        if (t < Time(self.planner.sun_up)):
            return 
        elif (t < Time(self.planner.meridian_flip)): 
            self.morning()
        elif (t < Time(self.planner.sun_down)):
            self.afternoon()
        else:
            return  

    def getDayPlan(self):
        self.planner.plan_the_day() 
        plan = {'utdate': '{0:s}-{1:s}-{2:s}'.format(self.planner.utdate[0:4], self.planner.utdate[4:6], self.planner.utdate[6:8]),
                'sun_up': self.planner.sun_up.isot, 
                'meridian_flip': self.planner.meridian_flip.isot, 
                'sun_down': self.planner.sun_down.isot}
        self.sio.emit('planToServer', plan)  
        # Use datetime because datetime.now() is local
        t = Time(datetime.now())
        if (t < Time(self.planner.sun_up)):
            self.scheduler.add_job(self.morning, 'date', 
                                   run_date=Time(self.planner.sun_up).datetime, replace_existing=True)
        if (t < Time(self.planner.meridian_flip)): 
            self.scheduler.add_job(self.afternoon, 'date', 
                                   run_date=Time(self.planner.meridian_flip).datetime, replace_existing=True)
        if (t < Time(self.planner.sun_down)):
            self.scheduler.add_job(self.evening, 'date',
                                   run_date=Time(self.planner.sun_down).datetime, replace_existing=True)

        return 
    def get_sun_coords(self):
        frame = AltAz(obstime=Time.now(), location=self.site)
        sun = get_sun(Time.now())
        return sun, frame

    def morning(self):
        print_message('Running morning script: {0:s}'.format((Time.now() - 7*u.h).isot[0:19]))
        sun, frame = self.get_sun_coords()
        # self.telescope.send_query('hW') # Wake up the telescope and start tracking         
        self.telescope.goto(sun) # Move the telescope 
        self.sio.emit("telescopeStatusToServer", "sun")
        self.center_sun()
        time.sleep(0.5)
        self.guider.send_query('S')
        time.sleep(0.5)
        self.guider.send_query(']')
        time.sleep(0.5)
        self.guider.send_query('E')
        time.sleep(0.5)
        self.guider.send_query("A")
        time.sleep(0.5)
        self.guider.send_query("X") 
        self.telescope.send_query('hW') # Wake up the telescope and start tracking 
        # Reactivate the guider here - remembering to recall PM 
        self.scheduler.add_job(self.update_guider, 'interval',seconds=10, replace_existing=True)     
        self.scheduler.add_job(self.camera.expose, 'interval',minutes=1, replace_existing=True)     
        return
    
    def afternoon(self):
        print_message('Running Afternoon script: {0:s}'.format((Time.now() - 7*u.h).isot[0:19]))
        self.sio.emit("telescopeStatusToServer", "med_flip")
        sun, frame = self.get_sun_coords()
        self.telescope.send_query('hN')
        time.sleep(5)
        self.telescope.goto(sun)
        self.sio.emit("telescopeStatusToServer", "sun")
        self.center_sun()
        time.sleep(0.5)
        self.guider.send_query('S')
        time.sleep(0.5)
        self.guider.send_query(']')
        time.sleep(0.5)
        self.guider.send_query('F')
        time.sleep(0.5)
        self.guider.send_query("A")
        time.sleep(0.5)
        self.guider.send_query("X") 
        self.telescope.send_query('hW') # Wake up the telescope and start tracking 
        # Reactivate the guider here - remembering to recall PM
        self.scheduler.add_job(self.update_guider, 'interval',seconds=10, replace_existing=True)  
        self.scheduler.add_job(self.camera.expose, 'interval',minutes=1, replace_existing=True)           
        return

    def evening(self):
        print_message('Running evening script: {0:s}'.format((Time.now() - 7*u.h).isot[0:19]))
        self.sio.emit("telescopeStatusToServer", 'parked')
        self.guider.send_query(']')
        self.telescope.send_query('hC')
        time.sleep(30)
        self.telescope.send_query('hN') # sleep the telescope 
        self.scheduler.add_job(self.update_guider, 'interval', hours=10, replace_existing=True)   
        self.scheduler.add_job(self.camera.expose, 'interval', hours=10, replace_existing=True)         
        return

    def update_guider(self):
        guider_status = self.guider.get_status()
        self.sio.emit('guiderStatusToServer', guider_status)

    def center_sun(self):
        return 


def print_message(msg, padding=True):
  if padding:
    print(''.join(np.repeat('-', 11 + len(msg) + 11)))
  print('{0:s} {1:s} {0:s}'.format(''.join(np.repeat('-', 10)), msg))
  if padding:
    print(''.join(np.repeat('-', 11 + len(msg) + 11)))


if __name__ == '__main__':
    x = expres_solar()
