import astropy.units as u
import socketio
import sqlalchemy as db

import yaml

from aiohttp import web
from astropy.time import Time
from datetime import datetime
from shutil import copyfile

sio = socketio.AsyncServer(async_mode='aiohttp', async_handlers=True,
    cors_allowed_origins='*')

app = web.Application() 


sio.attach(app)

class db_connection():
    def __init__(self):
        self.config = yaml.safe_load(open('solar_config.yml', 'r'))
        self.nohardware = self.config['no-hardware']
        if not self.nohardware:
            self.engine = db.create_engine(config['mysql_engine'])
            self.metadata = db.MetaData(bind=self.engine)
            self.environmentTable = db.Table('environment', self.metadata, autoload=True
                )
        else:
            print("Running Server in no hardware mode")
    def get24HEnvironment(self):
        if not self.nohardware:
            connection = self.engine.connect()
            t = (Time(datetime.utcnow()) - 24*u.h).datetime
            res = list(connection.execute(self.environmentTable.select().where(self.environmentTable.c.DATEOBS > t)))
            connection.close()
            time_array = [Time(x[1]).isot for x in res]
            t0 = [x[2] for x in res]
            t1 = [x[3] for x in res]
            t2 = [x[4] for x in res]
            h0 = [x[4] for x in res]
            return {'time':time_array, 't0':t0, 't1':t1, 't2':t2, 'h0':h0}
        else:
            return {'time':[], 't0':[], 't1':[], 't2':[], 'h0':[]}

    def getLastEntry(self):
        if not self.nohardware:
            connection = self.engine.connect()
            qr = self.environmentTable.select().order_by(self.environmentTable.c.ENVIRONMENTID.desc()).limit(1)
            res = list(connection.execute(qr))
            connection.close()
            time_array = [Time(x[1]).isot for x in res]
            t0 = [x[2] for x in res]
            t1 = [x[3] for x in res]
            t2 = [x[4] for x in res]
            h0 = [x[4] for x in res]
            return {'time':time_array, 't0':t0[0], 't1':t1[0], 't2':t2[0], 'h0':h0[0]}
        else:
            return {'time':[], 't0':[], 't1':[], 't2':[], 'h0':[]}


async def index(request):
    return web.Response(text='hello', content_type='text/html')

 
@sio.on('newWebClient')
async def newWebClient(sid, message):
    print('New Web Client')
    await sio.emit('newWebClient', 'hello')
    await sio.emit('environmentData', db_conn.get24HEnvironment())
    await sio.emit('updatePlan', {'sun_up': x.sun_up, 'utdate':x.utdate, 'meridian_flip':x.meridian_flip, 'sun_down':x.sun_down})
    # await sio.emit('environmentManagerToClient', x.environmentManager)

@sio.on('updatedEnvironment')
async def newWebClient(sid, message):
    print("Environment updated - sending new values")
    await sio.emit('updateEnvironment', db_conn.getLastEntry())
 
@sio.on('update')
async def update_variable(sid, data):
    for key in data:
        x.vars[key] = data
        print('Updating {0:s} with value {1:s}'.format(key, data[key]))
    await sio.emit('update', data)

@sio.on('webcam')
async def webcamImageReceived(sid, data):
    print('new webcam image')
    fh = data.split("\\")[-1]
    tobs = Time(fh.split('.jpg')[0].replace('_',':'))
    copyfile('/Volumes/solar/webcam/{0:s}'.format(fh), './webApp/static/assets/img/webcam_latest.jpg')
    await sio.emit('updateWebcam', tobs.iso[0:19])
    

@sio.on('planToServer')
async def planToServer(sid, data):
    print("Plan for new day received")
    x.utdate = data['utdate']
    x.sun_up = data['sun_up']
    x.meridian_flip = data['meridian_flip']
    x.sun_down = data['sun_down']
    await sio.emit('updatePlan', data)


@sio.on('telescopeStatusToServer')
async def telescopeStatusToServer(sid, message):
    print("Updating status of telescope")
    x.telescopeStatus = message
    await sio.emit('telescopeStatusToClients', message)
 


@sio.on('environmentManagerToServer')
async def environmentStatusToServer(sid, message):
    x.environmentManager = message
    await sio.emit('environmentManagerToClient', message)


@sio.on('sunIntensity')
async def update_sun_intensity(sid, data):
    print('updating sun intensity with value {0:f}'.format(data))
    await sio.emit('sunIntensity', data)

@sio.on('updateEnv')
async def updateEnv(sid, data):
    print('updating environment plot')
    await sio.emit('updateEnv', data)

@sio.on('guiderUpdate')
async def update_sun_intensity(sid, data):
    print('updating guider table')
    await sio.emit('guiderUpdate', data)

@sio.on('telescopeStatus')
async def telescopeStatus(sid, data):
    print('updating Telescope Status')
    await sio.emit('telescopeStatus', data)

@sio.on('clearTables')
async def clearTables(sid, data):
    print("Clearing data tables in GUI")
    await sio.emit('clearTables', 'hello')

@sio.on("disconnect")
def on_disconnect(sid):
    print("Client disconnected")

@sio.on("reconnect")
async def on_reconnect(sid):
    print("Client Reconnected")
    await sio.emit('newWebClient', 'hello')

@sio.on('guiderStatusToServer')
async def guiderStatusToServer(sid, data):
    print("New guider status data received")
    print(data['sun_intensity'])
    await sio.emit('guiderStatusToClient', data)

@sio.on('NewCalciumImageToServer')
async def NewCalciumImageToServer(sid, data):
    print("New Calcium image received")
    copyfile(data, './webApp/static/assets/img/calcium_latest.jpg')
    await sio.emit('updateCalciumImage', 'hello')
    
class variables():
    def __init__(self):
        self.vars = {'sunRA':'',
                     'sunDec':'',
                     'sunAlt':'',
                     'sunAz':'',
                     'initialize':'',
                     'observe':'',
                     'lostT':'',
                     'lostRH':'',
                     'environmentManager':'disconnected',
                     'weather':'cloudy'}

x = variables()
db_conn = db_connection()
app.router.add_get('/', index)
web.run_app(app, port=8081)


