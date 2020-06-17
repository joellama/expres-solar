#Solution based on https://stackoverflow.com/questions/49878953/issues-listening-incoming-messages-in-websocket-client-on-python-3-6

import websockets
import asyncio
import requests 
from bs4 import BeautifulSoup
import threading
import time
import numpy as np
import json 
import socketio
from asyncio import CancelledError
from contextlib import suppress

class expres_interface:
    def __init__(self):
        self.login_url = 'http://expres-test.local/login'
        self.request_url = 'http://expres-test.local/start_night'
        self.expresMgr = 'http://expres-test.local:5164/'
        self.session = requests.Session()    
        self.client = WebSocketClient()
        payload = {
            'login':'bizard',
            'passwd':'asdf',
            'form.submitted':'Log In',
            'came_from': '/observe/start_night'
        }
        post = self.session.post(self.login_url, data=payload)
        soup = BeautifulSoup(post.content.decode('UTF-8'), features="lxml")
        self.script_id_current = soup.find_all('input', attrs={'name':'script_id_current'})[0].get('value')
        self.logsheet_id_current = soup.find_all('input', attrs={'name':'logsheet_id_current'})[0].get('value')
        self.user_id = soup.find_all('input', attrs={'name':'user_id'})[0].get('value')  
        request = "logsheet-join"
        params = {'logsheet_id': self.logsheet_id_current,
                  'script_id': self.script_id_current,
                  'user_id': self.user_id
        }
        status, _ = self.askExpresTo(request, params)

        request = 'expres-add-active-observer'
        params = {'user_id':self.user_id}
        status, _ = self.askExpresTo(request, params)        

        # Start connection and get client connection protocol        
        self.loop = asyncio.get_event_loop()
        self.connection = self.loop.run_until_complete(self.client.connect())
        # Start listener and heartbeat 
        tasks = [
            asyncio.ensure_future(self.client.heartbeat(self.connection)),
            asyncio.ensure_future(self.client.receiveMessage(self.connection)),
        ]        
        self.ws_thread = threading.Thread(
            name='expres_ws',
            target = self.start_ws_loop,
            args=(tasks, self.session)
            )
        self.ws_thread.start()

    def logout(self):
            print("Logging out")
            # asyncio.gather(*asyncio.Task.all_tasks(self.loop)).cancel()
            
            self.client.disconnect()
            self.session.get('http://expres-test.local/logout')
            request = 'expres-remove-active-observer'
            status, _ = self.askExpresTo(request, {})
            self.session.close()

    def start_ws_loop(self, tasks, session):
        with self.session:
            self.loop.run_until_complete(asyncio.wait(tasks))    

    
    def stop(self):
        try:
            # run_forever() returns after calling loop.stop()
            self.loop.run_forever()
            tasks = Task.all_tasks()
            for t in [t for t in tasks if not (t.done() or t.cancelled())]:
                # give canceled tasks the last chance to run
                self.loop.run_until_complete(t)
        finally:
            self.loop.close()              

    def get_package(self, package_id):
        r = self.session.get('http://expres-test.local/observe/package/{0:d}/json'.format(package_id)).json()
        return r

    def askExpresTo(self, request, params):
        payload = {
            'method': request,
            'params': params,
            'jsonrpc': '2.0',
            'id': 'solar:{0:d}'.format(np.random.randint(1e3)),
        }
        payload = json.dumps(payload)
        res = self.session.post(self.expresMgr, payload)
        res_out = res.content.decode('utf-8')
        if 'result' in res_out:
            return True, res_out
        else:
            return False, res_out

    def prepare_package(self, pkg):
        pkgObject = {
            "object_id": pkg['object_id'],
            "package_id": pkg['package_id'],
            "program_id": pkg['program_id'],
            "object_type": pkg['object_type'],
            "preset_mode": pkg['preset_mode'].lower(),
            "preset_uses_sim": pkg['preset_uses_sim'].lower(),
            "pmode_id": pkg['pmode_id'],
            "script_id": pkg['script_id'],
            "nos_version": pkg['nos_version'],
            "name": pkg['object_name'],
            "plx_mas": pkg['plx_mas'],
            "pm": {
                "epoch": 2000.0,
                "ra_arcsecs": 0,
                "dec_arcsecs": 0
                },
            "rv": 0.0,
            "radec_required": False,
            "ra": pkg['ra'],
            "dec": pkg['dec'],
            "equinoxPrefix": 'J',
            "equinoxYear": 2000,
            "epoch": pkg['epoch'],
            "frame": pkg['frame'],
            "rotator": {
                "rotPA": 0.0,
                "rotFrame": "Target"
            },
            "vmag": pkg['vmag'],
            "exp_time": 10,#pkg['exp_time'],
            "sim_time": pkg['sim_time'],
            "sim_mode": pkg['sim_mode'],
            "succesful_exps": 0,
            "num_exp": 1,#pkg['num_exp'],
            "snr": pkg['snr'],
            "setpoint": pkg['setpoint'],
            "stop_condition": 'time',
            "log_comment": 'Prepared by Solar Telescope',
            "add_comment_to_fits": 'Nothing',
            "do_cal_mirror_check": False,
            "do_ext_flat_check":  False,
            "do_exp_meter_check":  False,
            "do_agitator_check":  False,
        }
        if pkg['object_type'].lower() == 'calibration':
            pkgObject['do_cal_mirror_check'] = True
        return pkgObject
    
    def observe_package(self, package_id=10394):
        r = self.get_package(package_id)
        package_name = r['pkg']['package_name']
        package_id = r['pkg']['package_id']
        script_id = r['pkg']['script_id']
        object_ids = [x['object_id'] for x in r['pkg']['lines']]
        package_items = [x['object_name'] for x in r['pkg']['lines']]
        package_payloads = [self.prepare_package(r['pkg']['lines'][jj]) for jj in range(len(package_items))]
        
        # First, we stage the package 
        request = "observer-ask-next-package"
        params = {'package_id':package_id, 'script_id':script_id}
        status, _ = self.askExpresTo(request, params)

        # Next, we confirm it got there 
        request = "observer-ask-current-package"
        params = {'package_id':package_id, 'script_id':script_id}
        status, _ = self.askExpresTo(request, params)
        
        # Now we observe - for now we are just observing the first item in the list, 
        #we need to loop and add in checks that the previous observation completed 
        #First, stage the object within the package
        for jj in range(len(package_items)):
            print("Starting: {0:s}".format(package_items[jj]))
            ## Do we need the cal mirror to be in or out? 
            # if package_payloads[jj]['object_type'].lower() == 'science':
            #     required_cal_mirror_state = 'out'
            # else:
            #     required_cal_mirror_state = 'in'
            # status, res = self.askExpresTo('adc-fci-stat', {})
            # if not required_cal_mirror_state in res: # Need to make sure this is a good check
            #     print("Moving Cal Injection Mirror to position {0:s}".format(required_cal_mirror_state))
            #     status, res = self.askExpresTo('adc-fci-{0:s}'.format(required_cal_mirror_state))
            #     while not required_cal_mirror_state in res:
            #         time.sleep(2)
            #         status, res = self.askExpresTo('adc-fci-stat')
            #     print("Cal Injection Mirror move complete")
            # else:
            #     print("Cal Injection Mirror already at position {0:s}".format(required_cal_mirror_state))
            
            # if package_payloads[jj]['object_name'].lower() == 'lfc':
            #   print("Turning on the LFC")
            #   do something to turn on the LFC
            #   time.sleep(40)
            request = "observer-ask-current-object"
            params = {'object_id': object_ids[jj], 'script_id':script_id}
            status, _ = self.askExpresTo(request, params)
            # Observe
            request = "macros-observe"
            params = {"object":package_payloads[jj]}
            status, _ = self.askExpresTo(request, params)
            time.sleep(0.2)
            # asyncio.get_event_loop().run_until_complete(wsrun('ws://expres-test.local:8842/ws/')) 
            print("Finishing: {0:s}".format(package_items[jj]))



class WebSocketClient:
    def __init__(self):
        self.sio = socketio.Client()  # This is the server for the solar telescope
        self.sio.connect('http://expres-test.local:8081') 
        pass
        
    async def connect(self):
        '''
            Connecting to webSocket server

            websockets.client.connect returns a WebSocketClientProtocol, which is used to send and receive messages
        '''
        self.connection = await websockets.client.connect('ws://expres-test.local:8842/ws/')
        if self.connection.open:
            print('Connection stablished. Client correcly connected')
            # Send greeting
            await self.sendMessage('Hey server, this is webSocket client')
            return self.connection

    async def disconnect(self):
        await self.connection.close()

    async def sendMessage(self, message):
        '''
            Sending message to webSocket server
        '''
        await self.connection.send(message)

    async def receiveMessage(self, connection):
        '''
            Receiving all server messages and handling them
        '''
        while True:
            try:
                _ = await connection.recv()
                msg = json.loads(_)
                if msg['packet_type'] == 'status':
                    if not 'agitator' in msg['module']:
                        print('expresModule')
                        self.sio.emit('expresModuleUpdate', msg) 
                if msg['packet_type'] == 'camera-time':
                    print('cameraTime')
                    self.sio.emit('expresCameraTime', msg) 
                if msg['packet_type'] == 'integration-count':
                    self.sio.emit('expresIntegrationCount', msg)
                # print('Received message from server: ' + str(message))
            except websockets.exceptions.ConnectionClosed:
                print('Connection with server closed')
                break
 
    async def heartbeat(self, connection):
        '''
        Sending heartbeat to server every 5 seconds
        Ping - pong messages to verify connection is alive
        '''
        while True:
            try:
                await connection.send('ping')
                await asyncio.sleep(5)
            except websockets.exceptions.ConnectionClosed:
                print('Connection with server closed')
                break

    async def end_session(self): # This is wrong
        loop = asyncio.new_event_loop()
        loop.call_soon_threadsafe(loop.stop)
        return
 

# if __name__ == '__main__':
#     x = expres_interface()
 
#     # x.observe_package(package_id=10394)