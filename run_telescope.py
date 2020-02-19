import astropy.units as u
import pandas as pd
import pytz
import socketio
import sqlalchemy as db

from apscheduler.schedulers.background import BackgroundScheduler
from astropy.coordinates import AltAz
from astropy.coordinates import EarthLocation
from astropy.coordinates import SkyCoord
from astropy.coordinates import get_sun
from astropy.table import Table
from astropy.time import Time
from datetime import datetime

 
from astropy.utils.iers import conf
from plan import expres_solar_planner
conf.auto_max_age = None

def timeSeconds(t):
    tnow = t.datetime
    midnight = tnow.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds = (tnow - midnight).seconds
    return seconds


class expres_solar():
    def __init__(self):
        self.planner = expres_solar_planner()
        self.sio = socketio.Client()    
        self.sio.connect('http://localhost:8081')
        # self.scheduler = BackgroundScheduler()
        # self.scheduler.start()
        # self.scheduler.add_job(self.getDayPlan, 'cron', hour=1, minute=0, replace_existing=True)        

        self.getDayPlan() # Also need to run this on the first run through 

    def getDayPlan(self):
        self.planner.plan_the_day() 
        plan = {'utdate': '{0:s}-{1:s}-{2:s}'.format(self.planner.utdate[0:4], self.planner.utdate[4:6], self.planner.utdate[6:8]),
                'sun_up': self.planner.sun_up['ISO_AZ'], 
                'meridian_flip': self.planner.meridian_flip['ISO_AZ'], 
                'sun_down': self.planner.sun_down['ISO_AZ']}
        self.sio.emit('planToServer', plan)  
        # Which of our schedules do we have left to do today? Take care of UTC (time.now() and AZ time )
        if (Time.now() < Time(self.planner.sun_up['ISO_UTC'])):
            self.scheduler.add_job(self.morning, 'date', 
                                   run_date=Time(self.planner.sun_up['ISO_AZ']).datetime,  replace_existing=True)
        if (Time.now() < Time(self.planner.meridian_flip['ISO_UTC'])): 
            self.scheduler.add_job(self.afternoon, 'date', 
                                   run_date=Time(self.planner.meridian_flip['ISO_AZ']).datetime,  replace_existing=True)
        if (Time.now() < Time(self.planner.sun_down['ISO_UTC'])):
            self.scheduler.add_job(self.end_day, 'date',
                                   run_date=Time(self.planner.sun_down['ISO_AZ']).datetime,  replace_existing=True)

        return 

    def morning(self):
        return
    
    def afternoon(self):
        return
    
    def evening(self):
        return

