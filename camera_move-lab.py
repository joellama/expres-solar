import matplotlib.pylab as plt
import numpy as np
import zwoasi as asi

import astropy.units as u

import serial 

import time 

from astropy.time import Time

class Camera:
    def __init__(self):
        try:
            asi.init('/home/jllama/asi_software/lib/x64/libASICamera2.so')
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
        self.camera.set_control_value(asi.ASI_GAIN, 60)
        self.camera.set_control_value(asi.ASI_EXPOSURE, 1500)
        self.camera.set_control_value(asi.ASI_WB_B, 99)
        self.camera.set_control_value(asi.ASI_WB_R, 75)
        self.camera.set_control_value(asi.ASI_GAMMA, 50)
        self.camera.set_control_value(asi.ASI_BRIGHTNESS, 50)
        self.camera.set_control_value(asi.ASI_FLIP, 0)
 
    def expose_simple(self, return_img=False, save_img=True, fh=None):
        self.camera.set_image_type(asi.ASI_IMG_RAW8)
        if save_img:
            if fh == None: 
                t = Time.now() - 7*u.h
                fh = './imgs/{0:s}.png'.format(t.isot[0:19].replace(':','_'))
            img = self.camera.capture(filename=fh) 
        else:
            img = self.camera.capture()
        if return_img: 
            return img    
        else:
            return     
 

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


class focusser:
    def __init__(self):
        sp = serial.Serial()
        sp.port = '/dev/SMI-rf'
        sp.baudrate = 1000000
        sp.parity = serial.PARITY_NONE
        sp.bytesize = serial.EIGHTBITS
        sp.stopbits = serial.STOPBITS_ONE
        sp.timeout = 1 
        sp.open()
        self.sp = sp
        return 

    def get_status(self):
        # Gets the current status of the guider 
        self.sp.write(str.encode('stat\r'))
        _ = self.sp.readline()
        status, step_position, step_rate, step_size, uptime, temperature = self.sp.readline().decode('utf-8').replace('\r','').replace('\n','').split(',')
        _ = self.sp.readline()
        return {'status': np.long(status), 'step_position': np.long(step_position), 'step_rate':np.long(step_rate), 'uptime': np.long(uptime),'temperature':np.float(temperature)}

    def focus(self):
        self.camera = Camera()
        img = self.camera.expose_simple(return_img=True, save_img=False) # returns a 2d array with the image file
        # Do the focus check and adjust here.
        return 




def take_lots_of_images():
    c = Camera()
    f = focusser()
    f.sp.flush()
    f.sp.write(str.encode('home\r'))
    time.sleep(0.5)
    _ = f.sp.readline()
    _ = f.sp.readline()
    print(_.decode('utf-8'))
    _ = f.sp.readline()
    start = 30000 
    stop = 40000
    step = 100 
    for jj in np.arange(start, stop, step, dtype=np.long):
        f.sp.write(str.encode('sa {0:d}\r'.format(jj)))
        if jj == start:
            time.sleep(1)
        _ = f.sp.readline()
        _ = f.sp.readline()
        _ = f.sp.readline()        
        c.expose_simple(save_img=True, fh='imgs/{0:06d}.jpg'.format(jj))
        
        stat = f.get_status()
        time.sleep(0.1)
        print("Guider step_position: {0:d}".format(stat['step_position']))

if __name__=='__main__':
    take_lots
