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
		try:
			asi.init('./camera_software/lib/mac/libASICamera2.dylib')
		except:
			pass
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
		self.camera.set_control_value(asi.ASI_GAIN, 50)
		self.camera.set_control_value(asi.ASI_EXPOSURE, 800)
		self.camera.set_control_value(asi.ASI_WB_B, 99)
		self.camera.set_control_value(asi.ASI_WB_R, 75)
		self.camera.set_control_value(asi.ASI_GAMMA, 50)
		self.camera.set_control_value(asi.ASI_BRIGHTNESS, 50)
		self.camera.set_control_value(asi.ASI_FLIP, 0)
	
	def expose(self):
		t = Time.now() - 7*u.h
		print('Exposing and saving file {0:s}'.format(t.strftime('%Y%m%d_%H%M%S')))
		utdate = '{0:d}{1:d}{2:d}'.format(Time.now().datetime.year, Time.now().datetime.month, Time.now().datetime.day)
		fh_fits = './data/{0:s}/{1:s}.fits'.format(utdate, Time.now().isot[0:19])
		fh_jpg = './data/{0:s}/{1:s}.jpg'.format(utdate, Time.now().isot[0:19])
		self.camera.set_image_type(asi.ASI_IMG_RAW8)
		img = self.camera.capture(filename=fh_jpg)			
		center, radius = find_disk(img=img, threshold=60)
		xpx, ypx = self.camera_info['MaxWidth'], self.camera_info['MaxHeight']
		x0 = np.max([0, np.long((center[1] - radius))])
		x1 = np.min([x0 + 2*radius, xpx])
		y0 = np.max([0, np.long((center[0] - radius))])
		y1 = np.min([ypx, y0 + 2*radius])
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
		hdu.writeto(t.strftime(fh_fits))

	def find_disk(img, threshold=1500):
	    """Finds the center and radius of a single solar disk present in the supplied image.

	    Uses cv2.inRange, cv2.findContours and cv2.minEnclosingCircle to determine the centre and 
	    radius of the solar disk present in the supplied image.

	    Args:
	        img (numpy.ndarray): greyscale image containing a solar disk against a background that is below `threshold`.
	        threshold (int): threshold of min pixel value to consider as part of the solar disk

	    Returns:
	        tuple: center coordinates in x,y form (int) 
	        int: radius
	    """
	    if img is None:
	        raise TypeError("img argument is None - check that the path of the loaded image is correct.")

	    if len(img.shape) > 2:
	        raise TypeError("Expected single channel (grayscale) image.")

	    blurred = cv2.GaussianBlur(img, (5, 5), 0)
	    mask = cv2.inRange(blurred, threshold, 255)
	    contours, img_mod = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

	    # Find and use the biggest contour
	    r = 0
	    for cnt in contours:
	        (c_x, c_y), c_r = cv2.minEnclosingCircle(cnt)
	        # cv2.circle(img, (round(c_x), round(c_y)), round(c_r), (255, 255, 255), 2)
	        if c_r > r:
	            x = c_x
	            y = c_y
	            r = c_r

	    # print("Number of contours found: {}".format(len(contours)))
	    # cv2.imwrite("mask.jpg", mask)
	    # cv2.imwrite("circled_contours.jpg", img)

	    if x is None:
	        raise RuntimeError("No disks detected in the image.")

	    return (round(x), round(y)), round(r)
