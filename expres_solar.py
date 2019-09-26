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
        self.scheduler.add_job(self.plan_the_day(), 'cron', hour=1, minute=0, replace_existing=True)
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
 
    def get_sun_for_whole_day(self):
        tnow = datetime.now().date()
        today = datetime(tnow.year, tnow.month, tnow.day, 0, 0, 0)
        tomorrow = datetime(today.year, today.month, today.day, 23, 59, 59)
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
        self.sun_up = self.sunpos.query('Alt > 20').iloc[0]
        self.sun_down = self.sunpos.query('Alt > 20').iloc[-1]
        self.meridian_flip = self.sunpos.iloc[self.sunpos['Alt'].idxmax() + 5] # Go 5 minutes past just to ensure meridian flip
        self.sio.emit('update', {'sun_up': '{0:s}'.format(self.sun_up['ISO_AZ'][11:-3]),
                                 'sun_down': '{0:s}'.format(self.sun_down['ISO_AZ'][11:-3]),
                                 'meridian_flip': '{0:s}'.format(self.meridian_flip['ISO_AZ'][11:-3])})
        self.scheduler.add_job(self.morning(), 'date', run_date=Time(self.sun_up['ISO_AZ']).datetime, 
                                replace_existing=True)
        self.scheduler.add_job(self.afternon(), 'date', run_date=Time(self.meridian_flip['ISO_AZ']).datetime, 
                                replace_existing=True)
        self.scheduler.add_job(self.end_day(), 'date', run_date=Time(self.sun_down['ISO_AZ']).datetime, 
                                replace_existing=True)   
        if self.just_initizalized == True:
          self.jun_initialized = False
          tnow = Time.now().mjd
          if (tnow > sun_up['MJD']) and (tnow <= meridian_flip['MJD']):
            # it's the morning 
            self.morning()
          elif (tnow < sun_down['MJD']) and (tnow > meridian_flip['MJD']):
            self.afternoon()
          elif (tnow < sun_up['MJD']) or (tnow > sun_down['MJD']):
            #its night time 
            self.end_day()
          else:
            print("Check your times, this shouldn't be an option")             


 
    def morning(self):
        print('Running Morning script')
        sun, frame = self.get_sun_coords()
        self.telescope.send_query('hW') # Wake up the telescope and start tracking 
        time.sleep(1)
        self.telescope.goto(sun) # Move the telescope 
        time.sleep(30)
        # Start tracking 
        # do all the guider activation here - recalling the AM settings 

    def afternoon(self):
        print('Running afternoon script')
        sun, frame = self.get_sun_coords()
        self.telescope.send_query('hN')
        time.sleep(1)
        self.telescope.goto(sun)
        time.sleep(30)
        self.telescope.send_query('hW') # Wake up the telescope and start tracking 
        # Reactivate the guider here - remembering to recall PM 

    def end_day(self):
        print('Running evening script')      
        self.telescope.send_query('hP')
        time.sleep(30)
        self.telescope.send_query('hN') # sleep the telescope
        # Stop guiding 

      
    def get_sun_coords(self):
        frame = AltAz(obstime=Time.now(), location=self.site)
        sun = get_sun(Time.now())
        return sun, frame


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
 

    def observe(self):
        # This routine checks if we can observe or not
        self.get_sun_coords()
        if self.sunAlt > 30:
            goodAlt = True
        else:
            goodAlt = False
        if goodAlt and goodAlt:
            self.observeStatus = 'True'
            self.sio.emit("observe", "True")
        else:
            self.observeStatus = 'False'
            self.sio.emit("observe", "False")



    def get_latest_cloudCam(self):
        files = os.listdir(self.cloudCamDir)
        if len(files) == 0:
            return 
        else:
            files.sort(key=lambda x: os.path.getmtime(x))
            latest = files[-1]
            self.sio.emit("cloudCam", latest)

class cloudCam():
    def __init__(self):
        self.img_dir = os.path.join(".","cloudCam","{0:s}")
        self.img_fh = os.path.join(self.img_dir ,"cloudcam_{1:s}.jpg")
        lib_file  = os.path.join('.', 'ASI','ASI SDK', 'lib', 'x64', 'ASICamera2.dll')
        if not os.path.exists(lib_file):
            print("Check location of ASICamera2.dll")
            return
        try:
            asi.init(lib_file)
        except:
            pass
        num_cameras = asi.get_num_cameras()
        if num_cameras == 0:
            print('No cameras found')
        cameras_found = asi.list_cameras()
        if num_cameras == 1:
            camera_id = 0
            print('Found one camera: %s' % cameras_found[0])
        else:
            print('Found %d cameras' % num_cameras)
            for n in range(num_cameras):
                print('    %d: %s' % (n, cameras_found[n]))
            # TO DO: allow user to select a camera
        self.camera_id = 0
        print('Using #%d: %s' % (camera_id, cameras_found[camera_id]))

    def expose(self):
        t = Time.now() - 7*u.h
        filename = self.img_fh.format(t.isot[0:10], t.isot[0:19]).replace(':','-')
        if not os.path.exists(self.img_dir.format(t.isot[0:10])):
            os.mkdir(self.img_dir.format(t.isot[0:10]))
        camera = asi.Camera(self.camera_id)
        camera_info = camera.get_camera_property()
        controls = camera.get_controls()
        # Use minimum USB bandwidth permitted
        camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD,
            camera.get_controls()['BandWidth']['MinValue'])
        camera.disable_dark_subtract()
        camera.set_control_value(asi.ASI_GAIN, 150)
        camera.set_control_value(asi.ASI_EXPOSURE, 30000)
        camera.set_control_value(asi.ASI_WB_B, 99)
        camera.set_control_value(asi.ASI_WB_R, 75)
        camera.set_control_value(asi.ASI_GAMMA, 50)
        camera.set_control_value(asi.ASI_BRIGHTNESS, 50)
        camera.set_control_value(asi.ASI_FLIP, 0)
        try:
            # Force any single exposure to be halted
            camera.stop_video_capture()
            camera.stop_exposure()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            pass
        camera.set_image_type(asi.ASI_IMG_RGB24)
        print('Capturing a single, color image')
        camera.capture(filename=filename)
        x.sio.emit('update', {'cloudCam':filename})
        return filename



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

 
 
