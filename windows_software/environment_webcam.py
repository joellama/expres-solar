import astropy.units as u
import numpy as np
import os
import socketio
import zwoasi as asi
from PIL import Image
from astropy.time import Time
from time import sleep
import json

def timeSeconds():
    tnow = (Time.now() - 7*u.h).datetime
    midnight = tnow.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds = (tnow - midnight).seconds
    return seconds

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)

if __name__ == "__main__":
    tstart = 6*u.h
    tend = 19*u.h
    sio = socketio.Client()
    sio.connect('http://10.10.115.156:8081')
    env_filename = os.getenv('ZWO_ASI_LIB')
    asi.init(env_filename)
    num_cameras = asi.get_num_cameras()
    if num_cameras == 0:
        print("No camera found")
        sys.exit(0)
    camera_id = 0
    camera = asi.Camera(camera_id)
    camera_info = camera.get_camera_property
    controls = camera.get_controls()
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
    camera.set_image_type(asi.ASI_IMG_RGB24)
    tstart_seconds = tstart.to(u.s).value
    tend_seconds = tend.to(u.s).value
    while True:
        if ((timeSeconds() > tstart_seconds) and (timeSeconds() < tend_seconds)):
            print("Capturing image")
            filename = os.path.join('Z:','webcam',(Time.now() - 7*u.h).isot[0:19].replace(':','_')+'.jpg')
            x = camera.capture(filename=filename)
            print("Captured image, saving it now")
            sio.emit('webcam', filename)
            print('sleeping for 60s')
            sleep(60)
