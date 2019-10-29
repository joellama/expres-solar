import pandas as pd
import socketio
from time import strptime, sleep
from astropy.time import Time
import numpy as np 
import os 
import astropy.units as u 

def print_message(msg, padding=True):
  if padding:
    print(''.join(np.repeat('-', 11 + len(msg) + 11)))
  print('{0:s} {1:s} {0:s}'.format(''.join(np.repeat('-', 10)), msg))
  if padding:
    print(''.join(np.repeat('-', 11 + len(msg) + 11)))

def get_temperature(sio):
    fh = os.path.join('/', 'Volumes', 'data', 'environment_data', 'thorlabs.csv')
    if os.path.exists(fh):
        df = pd.read_csv(fh, delimiter=';', header=17, engine='python')
        x = df.iloc[-1, :]
        t = Time('{0:04d}-{1:02d}-{2:02d}T{3:s}'.format(np.long(x['Date'].split(' ')[2]),
                                                        strptime(x['Date'].split(' ')[0], '%b').tm_mon,
                                                        np.long(x['Date'].split(' ')[1]),
                                                        x['Time']))
        sio.emit('updateEnv', {'Time': t.isot,
                                 'Temp':float(x.iloc[3]),
                                 'Humidity': float(x.iloc[4])
                                 })
    else:
        warnings.warn("File {0:s} not found".format(fh))


if __name__ == "__main__":
	sio = socketio.Client()
	sio.connect('http://localhost:8081')
	while True:
		print_message('Updating Temp/Humidity: {0:s}'.format((Time.now() - 7*u.h).iso[0:19]), padding=False)
		get_temperature(sio)
		sleep(120)
