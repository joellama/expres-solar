import astropy.units as u
import astropy.units as u
import numpy as np
import os
import socketio
import socketio
import zwoasi as asi

from astropy.time import Time
from time import sleep


def capture(camera):
    print("Capturing image")
    time_str = (Time.now() - 7*u.h).isot[0:19].replace(':','-')
    camera.capture(os.path.join('webcam', time_str))
    print("Captured image {0:s}".format(time_str))

def timeSeconds():
    tnow = (Time.now() - 7*u.h).datetime
    midnight = tnow.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds = (tnow - midnight).seconds
    return seconds


if __name__ == "__main__":
    sio = socketio.Client()
    sio.connect('http://10.10.115.156:8081')
    env_filename = os.getenv('ZWO_ASI_LIB')
    asi = asi.init(env_filename)
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
            capture(camera)
            sio.emit('environmentWebcam', 'captured')
            sleep(dt)
