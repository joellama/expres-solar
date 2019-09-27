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