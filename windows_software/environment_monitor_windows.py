 
from time import strptime, sleep
from astropy.time import Time
import numpy as np 
import socketio
import astropy.units as u 
# from apscheduler.schedulers.background import BackgroundScheduler


from py_thorlabs_tsp import ThorlabsTsp01B, ThorlabsTsp01BException
import sqlalchemy as db


class environment_data():
    def __init__(self, dt=60):
        self.engine = db.create_engine("mysql+pymysql://solar:4rp%V5zQgiXEecRRv@10.10.115.149:3307/solar")
        self.sio = socketio.Client()
        self.sio.connect('http://10.10.115.156:8081')

        while True:
            self.log_data()
            sleep(dt)

    def log_data(self):
        t= Time.now() - 7*u.h
        # print_message('Getting environment data: {0:s}'.format(t.isot[0:19]), padding=False)    
        try:
            sensor = ThorlabsTsp01B()
            t0 = float(sensor.measure_temperature())
            t1 = float(sensor.measure_temperature('th1'))
            t2 = float(sensor.measure_temperature('th2'))
            h = sensor.measure_humidity()
            sensor.release()
            connection = self.engine.connect()
            metadata = db.MetaData(bind=self.engine)
            temps = db.Table('environment', metadata, autoload=True)
            connection.execute(temps.insert().values(T0=t0, T1=t1, T2=t2, H0=h))
            connection.close()
            self.sio.emit('updatedEnvironment', 'now')

        except ThorlabsTsp01BException as e:
            print(e)
            pass
 
def print_message(msg, padding=True):
    if padding:
        print(''.join(np.repeat('-', 11 + len(msg) + 11)))
        print('{0:s} {1:s} {0:s}'.format(''.join(np.repeat('-', 10)), msg))
    if padding:
        print(''.join(np.repeat('-', 11 + len(msg) + 11)))

if __name__ == '__main__':
    x = environment_data(dt=120)
