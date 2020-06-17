import socketio
import threading 



solar_sio = socketio.Client()

class solarListener(): 
    global solar_sio
    def __init__(self):
        solar_sio.connect('http://expres-test.local:8081/')


@solar_sio.on('expresModuleUpdate')
def on_message(data):
    global expres_status
    expres_status = data

@solar_sio.on('expresCameraTimeUpdate')
def on_camera_time(data):
    global camera_time 
    camera_time = data

@solar_sio.on('expresIntegrationCountUpdate')
def on_camera_time(data):
    global integration_time 
    integration_time = data    


if __name__=='__main__':
    global expres_status
    global camera_time 
    global integration_time
    camera_time = {}
    expres_status = {}
    integration_time = {}
    x = threading.Thread(name='solarListener',
        target=solarListener())