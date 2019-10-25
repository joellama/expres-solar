import socketio

from aiohttp import web


sio = socketio.AsyncServer(async_mode='aiohttp', async_handlers=True)

app = web.Application()

sio.attach(app)



async def index(request):
    return web.Response(text='hello', content_type='text/html')

 
@sio.on('newWebClient')
async def newWebClient(sid, message):
	print('New Web Client')
	await sio.emit('newWebClient', 'hello')
# 	# sio.emit('iso', x.iso)
# 	# sio.emit('sunRA', x.sunRA)
# 	# sio.emit('sunDec', x.sunDec)
# 	# sio.emit('sunAlt', x.sunAlt)
# 	# sio.emit('sunAz', x.sunAz)
# 	# sio.emit('initialize', x.initialize)
# 	# sio.emit('utdate', x.utdate)
# 	# sio.emit('observe', x.observe)
# 	# sio.emit('lostT', x.lostT)
# 	# sio.emit('lostRH', x.lostRH)
# 	# # sio.emit('mjd', mjd)

@sio.on('update')
async def update_variable(sid, data):
	for key in data:
		x.vars[key] = data
		print('Updating {0:s} with value {1:s}'.format(key, data[key]))
	await sio.emit('update', data)
 
@sio.on('sunIntensity')
async def update_sun_intensity(sid, data):
	print('updating sun intensity with value {0:f}'.format(data))
	await sio.emit('sunIntensity', data)

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

class variables():
	def __init__(self):
		self.vars = {'mjd':'',
					 'utdate':'hello',
					 'iso':'',
					 'sunRA':'',
					 'sunDec':'',
					 'sunAlt':'',
					 'sunAz':'',
					 'initialize':'',
					 'observe':'',
					 'lostT':'',
					 'lostRH':'',
					 'weather':'cloudy'}

x = variables()
app.router.add_get('/', index)
web.run_app(app, port=8081)


