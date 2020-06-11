import astropy.units as u
import socketio
import sqlalchemy as db

import yaml
import logging

from aiohttp import web
from astropy.time import Time
from datetime import datetime
from shutil import copyfile

sio = socketio.AsyncServer(async_mode='aiohttp', async_handlers=True,
    cors_allowed_origins='*', access_log=None)
intensityCounter = 0
app = web.Application() 

logging.basicConfig(filename='/Volumes/solar/solar_logs/server.log', level=logging.WARNING,
    format="[%(asctime)s][%(levelname)s] %(message)s")

sio.attach(app)

class db_connection():
    def __init__(self):
        print("Server log file saved to {0:s}".format('/Volumes/solar/server.log'))
        config = yaml.safe_load(open('solar_config.yml', 'r'))
        self.engine = db.create_engine(config['mysql_engine'])
        self.metadata = db.MetaData(bind=self.engine)
        self.environmentTable = db.Table('environment', self.metadata, autoload=True
            )
        self.intensityTable = db.Table('intensity', self.metadata, autoload=True)
        self.intensityCounter = 0

    def get24HEnvironment(self):
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

    def getLastEntry(self):
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

    def insertIntensity(self, value):
        if self.intensityCounter == 6: # We don't want to save every single value
            connection = self.engine.connect()
            connection.execute(self.intensityTable.insert().values(INTENSITY=value))
            connection.close()
            self.intensityCounter = 0
        else:
            self.intensityCounter += 1

    def getTodayIntensity(self):
        connection = self.engine.connect()
        t = datetime.now()
        tsearch = datetime(t.year, t.month, t.day)
        res = list(connection.execute(self.intensityTable.select().where(self.intensityTable.c.DATEOBS > tsearch)))
        connection.close()
        time_array = [Time(x[1]).isot for x in res]
        intens = [x[2] for x in res]
        return {'time':time_array, 'intensity':intens}
        

async def index(request):
    return web.Response(text='hello', content_type='text/html')


 
@sio.on('newWebClient')
async def newWebClient(sid, message):
    logging.info("New web client connected")
    # print('New Web Client')
    await sio.emit('update', x.vars)
    # await sio.emit('newWebClient', 'hello')
    await sio.emit('environmentData', db_conn.get24HEnvironment())
    await sio.emit('intensityData', db_conn.getTodayIntensity())
    await sio.emit('logfile', {'logfile':read_logfile()})
    # await sio.emit('updatePlan', {'sun_up': x.sun_up, 'utdate':x.utdate, 'meridian_flip':x.meridian_flip, 'sun_down':x.sun_down})
    # await sio.emit('environmentManagerToClient', x.environmentManager)


def read_logfile():
    try: 
        with open('/Volumes/solar/solar_logs/{0:s}.log'.format(Time.now().isot[0:10]), 'r') as file:
            data = file.read()
    except:
        data = ""
    return data


@sio.on('update')
async def update(sid, data):
    for key in data.keys():
        x.vars[key] = data[key]
        if type(data[key]) != str:
            logging.info('{0:s} - {1:s}'.format(key, str(data[key])))
        else:
            logging.info('{0:s} - {1:s}'.format(key, data[key]))
        if key == 'guider_sun_intensity': 
                db_conn.insertIntensity(float(data[key]))
 

    await sio.emit('update', data)

@sio.on('updateIntensity')
async def updateIntensity(sid, message):
    # print("Environment updated - sending new values")
    try:
        data = db_conn.getTodayIntensity()
        # data['intensity'] = 10 - data['intensity']
        logging.info("New intensity data")
        await sio.emit('intensityData', data)
    except:
        logging.warning("Failed to get intensity data")
        pass

@sio.on('updateEnvironment')
async def updateEnvironment(sid, message):
    # print("Environment updated - sending new values")
    try:
        data = db_conn.get24HEnvironment()
        logging.info('New Environment data')
        await sio.emit('environmentData', data)
    except:
        logging.warning("Failed to get environment data")
        pass

@sio.on('webcam')
async def webcamImageReceived(sid, data):
    logging.info('New Solar disk image')
    fh = data.split("\\")[-1]
    tobs = Time(fh.split('.jpg')[0].replace('_',':'))
    copyfile('/Volumes/solar/webcam/{0:s}'.format(fh), './webApp/static/assets/img/webcam_latest.jpg')
    await sio.emit('updateWebcam', tobs.iso[0:19])
     

@sio.on("disconnect")
def on_disconnect(sid):
    logging.info("Client disconnected")

@sio.on("reconnect")
async def on_reconnect(sid):
    logging.info("Client reconnected")
    await sio.emit('newWebClient', 'hello')

# @sio.on('guiderStatusToServer')
# async def guiderStatusToServer(sid, data):
#     print("New guider status data received")
#     print(data['sun_intensity'])
#     await sio.emit('guiderStatusToClient', data)

@sio.on('NewCalciumImageToServer')
async def NewCalciumImageToServer(sid, data):
    logging.info("New solar disk image")
    copyfile(data, './webApp/static/assets/img/calcium_latest.jpg')
    await sio.emit('updateCalciumImage', 'hello')
    
class variables():
    def __init__(self):
        self.vars = {}

x = variables()
db_conn = db_connection()

app.router.add_get('/', index)
web.run_app(app, port=8081, access_log=None)


