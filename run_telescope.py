import astropy.units as u
import numpy as np 
import pandas as pd
import pytz
import socketio
import sqlalchemy as db
import time
import yaml

from apscheduler.schedulers.background import BackgroundScheduler
from astropy.coordinates import AltAz
from astropy.coordinates import EarthLocation
from astropy.coordinates import SkyCoord
from astropy.coordinates import get_sun
from astropy.table import Table
from astropy.time import Time
from astropy.utils.iers import conf
from camera import Camera
from datetime import datetime
from guider import Guider
from plan import expres_solar_planner
from telescope import Telescope
conf.auto_max_age = None

def timeSeconds(t):
    tnow = t.datetime
    midnight = tnow.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds = (tnow - midnight).seconds
    return seconds


class expres_solar():
    def __init__(self):
        self.site = EarthLocation.of_site('lowell')
        self.tz = pytz.timezone('US/Arizona')     
        self.systemBusy = False
        self.guider = Guider()   
        self.camera = Camera()
        self.planner = expres_solar_planner()
        self.sio = socketio.Client()    
        self.sio.connect('http://localhost:8081')
        self.telescope = Telescope()
        self.scheduler = BackgroundScheduler()
        self.routine = 'evening'
        self.scheduler.start()
        self.jobs = {}
        # start all continuous jobs
        self.jobs['getDayPlan'] = self.scheduler.add_job(self.getDayPlan, 
            'cron', hour=1, minute=0, replace_existing=True, id='getDayPlan') 
        self.jobs['getEnvironment'] = self.scheduler.add_job(self.updateEnvironment, 
            'interval',  minutes=10, replace_existing=True, id='updateEnvironment')
        # self.jobs['getIntensity'] = self.scheduler.add_job(self.updateIntensity, 
        #     'interval',  minutes=1, replace_existing=True, id='updateIntensity')        
        # self.jobs['printJobs'] = self.scheduler.add_job(self.get_list_of_jobs,
        #     'interval', minutes=1, replace_existing=True, id='list_of_jobs') 
        # self.jobs['update_guider'] = self.scheduler.add_job(self.update_guider, 
        #     'interval', hours=1, replace_existing=True, id='update_guider')
        # self.jobs['update_telescope'] = self.scheduler.add_job(self.update_telescope, 
        #     'interval', hours=1, replace_existing=True, id='update_telescope')     
        # self.jobs['camera_expose'] = self.scheduler.add_job(self.camera.expose, 
        #     'interval', hours=1, replace_existing=True, id='camera_expose')
        self.config = yaml.safe_load(open('solar_config.yml', 'r'))
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

    def emit(self, values):
        self.sio.emit('update', values)
        return

    def getDayPlan(self):
        if self.config['startup_type'] == 'altitude':
            print_message("Planning day using altitude")
            self.planner.plan_the_day_altitude() 
        else: 
            print_message("Planning day using specified time")
            self.planner.plan_the_day_time()
        plan = {'utdate': '{0:s}-{1:s}-{2:s}'.format(self.planner.utdate[0:4], self.planner.utdate[4:6], self.planner.utdate[6:8]),
                'sun_up': self.planner.sun_up.isot[11:16], 
                'meridian_flip': self.planner.meridian_flip.isot[11:16], 
                'sun_down': self.planner.sun_down.isot[11:16]}
        self.emit(plan)  
        # Use datetime because datetime.now() is local
        t = Time(datetime.now())
        if (t < Time(self.planner.sun_up)):
            self.scheduler.add_job(self.morning, 'date', 
                                   run_date=Time(self.planner.sun_up).datetime, 
                                   replace_existing=True, id='morning')
        if (t < Time(self.planner.meridian_flip)): 
            self.scheduler.add_job(self.afternoon, 'date', 
                                   run_date=Time(self.planner.meridian_flip).datetime, 
                                   replace_existing=True, id='afternoon')
        if (t < Time(self.planner.sun_down)):
            self.scheduler.add_job(self.evening, 'date',
                                   run_date=Time(self.planner.sun_down).datetime, 
                                   replace_existing=True, id='evening')

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
        self.telescope.send_query('hW') # Wake up the telescope and start tracking 
        self.update_telescope()
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
        # Reactivate the guider here - remembering to recall PM 
        self.jobEndTime = (self.planner.meridian_flip - 2*u.min).datetime
        self.jobs['update_guider'] = self.scheduler.add_job(self.update_guider, 
            'interval',seconds=10, replace_existing=True, id='update_guider',
            end_date=self.jobEndTime)
        self.jobs['update_telescope'] = self.scheduler.add_job(self.update_telescope, 
            'interval',seconds=10, replace_existing=True, id='update_telescope',
            end_date=self.jobEndTime)     
        self.jobs['camera_expose'] = self.scheduler.add_job(self.camera.expose, 
            'interval', seconds=20, replace_existing=True, id='camera_expose',
            end_date=self.jobEndTime) 
        self.emit({'routine':'morning'})
        self.routine = 'morning'
        return
    
    def afternoon(self):     
        print_message('Running Afternoon script: {0:s}'.format((Time.now() - 7*u.h).isot[0:19]))
        sun, frame = self.get_sun_coords()
        self.telescope.send_query('hW')
        self.telescope.goto(sun)   
        time.sleep(2)
        self.update_telescope()
        mount_pos = self.telescope_status['telescope_orientation']
        if 'West' in mount_pos:
            self.telescope.send_query('Mf')
            time.sleep(120)
        self.guider.send_query('S')
        time.sleep(0.5)
        self.guider.send_query(']')
        time.sleep(0.5)
        self.guider.send_query('F')
        time.sleep(0.5)
        self.guider.send_query("A")
        time.sleep(0.5)
        self.guider.send_query("X") 
        self.jobEndTime = (self.planner.sun_down - 2*u.min).datetime
        self.jobs['update_guider'] = self.scheduler.add_job(self.update_guider, 
            'interval',seconds=10, replace_existing=True, id='update_guider',
            end_date=self.jobEndTime)
        self.jobs['update_telescope'] = self.scheduler.add_job(self.update_telescope, 
            'interval',seconds=10, replace_existing=True, id='update_telescope',
            end_date=self.jobEndTime)     
        self.jobs['camera_expose'] = self.scheduler.add_job(self.camera.expose, 
            'interval', seconds=20, replace_existing=True, id='camera_expose',
            end_date=self.jobEndTime)         
        self.emit({'routine':'afternoon'})     

        self.routine = 'afternoon'
        return

    def evening(self):   
        time.sleep(120)
        print_message('Running evening script: {0:s}'.format((Time.now() - 7*u.h).isot[0:19]))
        self.guider.send_query(']')
        self.telescope.send_query('hC')
        time.sleep(5)
        self.telescope.send_query('hN') # sleep the telescope 
        self.emit({'routine':'evening'})  
        self.routine = 'evening' 
        return

    def update_guider(self):
        guider_status = self.guider.get_status(save_status=False)
        self.emit(guider_status)
        x_act = guider_status['guider_x_ra_pos'] 
        y_act = guider_status['guider_y_ra_pos'] 
        x_ref = self.config['guider_x_center']
        y_ref = self.config['guider_y_center']
        x_diff = np.abs(x_act - x_ref)
        y_diff = np.abs(y_act - y_ref)
        # print_message("update guider condition: {0:02d}, {0:02d}".format(xpos, ypos))
        if ( ((x_diff > 3) or (y_diff > 3)) and ((x_act != 255) or (y_act != 255)) ): 
            print_message("Attempting to center sun")
            self.center_sun()
            guider_status = self.guider.get_status(save_status=False)
            self.emit(guider_status)
        return

    def update_telescope(self):
        self.telescope_status = self.telescope.get_status()
        self.emit(self.telescope_status)
        return

    def center_sun(self):
        try:
            self.scheduler.pause_job('update_guider')
            self.scheduler.pause_job('update_telescope')
            time.sleep(0.2)
        except:
            pass
        self.guider.send_query(']')
        time.sleep(0.2)
        guider_status = self.guider.get_status()
        if len(guider_status) == 0:
            guider_status = self.guider.get_status()
        x_pos = guider_status['guider_x_ra_pos']
        y_pos = guider_status['guider_y_ra_pos']
        mount_pos = self.telescope_status['telescope_orientation']
        if 'West' in mount_pos: # Morning 
            move_array = ['w', 'e', 'n', 's']
        elif 'East' in mount_pos: # afternoon
            move_array = ['e', 'w', 'n', 's']
        else: 
            print("MOUNT STATUS UNKNOWN")
            if self.routine != "evening":
                self.scheduler.resume_job('update_guider')
                self.scheduler.resume_job('update_telescope')
            return
        steps = 0 
        step_max = 200
        if (x_pos != 255) and (y_pos != 255): # We have signal 
            # First fix x_pos 
            self.telescope.send_query('RM')
            if x_pos < (self.config['guider_x_center'] - 1):
                while ((x_pos < (self.config['guider_x_center'])) and (x_pos != 0) and (x_pos != 255) and (steps < step_max)): 
                    self.telescope.send_query('M{0:s}50'.format(move_array[0]))
                    guider_status = self.guider.get_status()
                    print("x_pos = {0:d}".format(x_pos))
                    x_pos = guider_status['guider_x_ra_pos']                    
                    time.sleep(0.2)
                    steps += 1
                self.telescope.send_query("Q")
            elif (x_pos > (self.config['guider_x_center'] + 1)): 
                while ((x_pos > (self.config['guider_x_center'])) and (x_pos != 0) and (x_pos != 255) and (steps < step_max)): 
                    self.telescope.send_query('M{0:s}50'.format(move_array[1]))
                    guider_status = self.guider.get_status()
                    print("x_pos = {0:d}".format(x_pos))
                    x_pos = guider_status['guider_x_ra_pos']                    
                    time.sleep(0.2)
                    steps += 1 
                self.telescope.send_query("Q")
            print("RA aligned")
            steps = 0  
            if y_pos < (self.config['guider_y_center'] - 1):
                while ((y_pos < (self.config['guider_y_center'])) and (y_pos != 0) and (y_pos != 255) and (steps < step_max)): 
                    self.telescope.send_query('M{0:s}50'.format(move_array[2]))
                    guider_status = self.guider.get_status()
                    print("y_pos = {0:d}".format(y_pos))
                    y_pos = guider_status['guider_y_ra_pos']                    
                    time.sleep(0.2)
                    steps += 1
                self.telescope.send_query("Q")
            elif y_pos > (self.config['guider_y_center'] + 1): 
                while ((y_pos > (self.config['guider_y_center'])) and (y_pos != 0) and (y_pos != 255) and (steps < step_max)): 
                    self.telescope.send_query('M{0:s}50'.format(move_array[3]))
                    guider_status = self.guider.get_status()
                    print("y_pos = {0:d}".format(y_pos))
                    y_pos = guider_status['guider_y_ra_pos']                    
                    time.sleep(0.2)
                    steps += 1
                self.telescope.send_query("Q")
            print("DEC aligned")   
            self.telescope.send_query("Q")         
        else: # We have no signal
            print_message("No signal from Sun to align")
        self.telescope.send_query("RG")
        self.guider.send_query("Q") # update guider mech offset
        self.telescope.send_query('hW')
        self.guider.send_query('A')
        self.scheduler.resume_job('update_guider')
        self.scheduler.resume_job('update_telescope')

        return 


    def get_list_of_jobs(self):
        jobs = {}
        for job in self.scheduler.get_jobs():
            jobs[job.name] = '%s' % job.trigger
            try:
                self.emit({'job_guider':jobs['expres_solar.update_guider'], 
                   'job_telescope':jobs['expres_solar.update_telescope'], 
                   'job_day_plan':jobs['expres_solar.getDayPlan'],
                   'job_camera_expose':jobs['Camera.expose']})
            except:
                pass
    
    def updateEnvironment(self):
        self.sio.emit('updateEnvironment', 'test')
        return

    def updateIntensity(self):
        self.sio.emit('updateIntensity', 'test')
        return

def print_message(msg, padding=True):
  if padding:
    print(''.join(np.repeat('-', 11 + len(msg) + 11)))
  print('{0:s} {1:s} {0:s}'.format(''.join(np.repeat('-', 10)), msg))
  if padding:
    print(''.join(np.repeat('-', 11 + len(msg) + 11)))


if __name__ == '__main__':
    x = expres_solar()
