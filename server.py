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
	# sio.emit('iso', x.iso)
	# sio.emit('sunRA', x.sunRA)
	# sio.emit('sunDec', x.sunDec)
	# sio.emit('sunAlt', x.sunAlt)
	# sio.emit('sunAz', x.sunAz)
	# sio.emit('initialize', x.initialize)
	# sio.emit('utdate', x.utdate)
	# sio.emit('observe', x.observe)
	# sio.emit('lostT', x.lostT)
	# sio.emit('lostRH', x.lostRH)
	# # sio.emit('mjd', mjd)

@sio.on('update')
async def update_variable(sid, data):
	for key in data:
		x.vars[key] = data
		print('Updating {0:s} with value {1:s}'.format(key, data[key]))
	await sio.emit('update', data)
 	
@sio.on('sunPlot')
async def update_variable(sid, data):
	await sio.emit('sunPlot', data)

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
web.run_app(app, port=8080)


