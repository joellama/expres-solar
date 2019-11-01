import argparse
import json
import numpy as np
import os
import pandas as pd
import pytz
import requests
import socketio
import sys
import time
import warnings

from datetime import datetime


import astropy.units as u

from astropy.coordinates import AltAz
from astropy.coordinates import EarthLocation
from astropy.coordinates import SkyCoord
from astropy.coordinates import get_sun
from astropy.table import Table
from astropy.time import Time
from astropy.io import fits 

import zwoasi as asi

class Camera():
	def __init__(self):
		asi.init('./camera_software/lib/mac/libASICamera2.dylib')
		num_cameras = asi.get_num_cameras()
		if num_cameras == 0:
		    print('No cameras found')
		    sys.exit(0)		
		self.camera = asi.Camera(0)
		self.camera_info = self.camera.get_camera_property()
		self.controls = self.camera.get_controls()
		self.camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD, 
			self.camera.get_controls()['BandWidth']['MinValue'])
		self.camera.disable_dark_subtract()
		self.camera.set_control_value(asi.ASI_GAIN, 75)
		self.camera.set_control_value(asi.ASI_EXPOSURE, 1000)
		self.camera.set_control_value(asi.ASI_WB_B, 99)
		self.camera.set_control_value(asi.ASI_WB_R, 75)
		self.camera.set_control_value(asi.ASI_GAMMA, 50)
		self.camera.set_control_value(asi.ASI_BRIGHTNESS, 50)
		self.camera.set_control_value(asi.ASI_FLIP, 0)
		self.camera.set_image_type(asi.ASI_IMG_RAW16)
	
	def expose(self):
		t = Time.now() - 7*u.h
		print('Exposing and saving file {0:s}'.format(t.strftime('%Y%m%d_%H%M%S')))
		img = self.camera.capture()		
		hdr = fits.Header()
		hdr['SIMPLE'] = "T"
		hdr['BITPIX'] = -32
		hdr['NAXIS'] = 2 
		hdr['NAXIS1'] = img.shape[0]
		hdr['NAXIS2'] = img.shape[1]
		hdr['OBSERVAT'] = 'Lowell Observatory'
		hdr['TELESCOP'] = 'Solar Telescope'
		hdr['INSTRUME'] = 'Calcium K'
		hdr['OBJECT'] = 'Sun'
		hdr['TIMESYS'] = 'UTC'
		hdr['UTDATE'] = t.strftime('%Y%m%d')
		hdr['DATE-OBS'] = t.fits
		hdr['EXPTIME'] = self.camera.get_control_values()['Exposure']
		hdr['GAIN'] = self.camera.get_control_values()['Gain']
		hdr['FLIP'] = self.camera.get_control_values()['Flip']
		hdr['EXPTIME'] = self.camera.get_control_values()['Exposure']
		hdr['COOLERON'] = self.camera.get_control_values()['CoolerOn']
		hdr['OFFSET'] = self.camera.get_control_values()['Offset']
		
		hdu = fits.PrimaryHDU(img, header=hdr)
		hdu.writeto(t.strftime('{0:s}.fits'.format(t.strftime('%Y%m%d_%H%M%S'))))