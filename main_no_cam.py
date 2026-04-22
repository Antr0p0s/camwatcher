import time
import threading

from resources.tempWorker import temperature_acquisition_thread
from resources.pressureWorker import pressure_acquisition_thread
from resources.no_cam_workers import save_data

from dotenv import load_dotenv
import os

load_dotenv()

DEV_MODE = os.getenv("ENVIRONMENT") == 'dev'
print(f'Running in {"DEV" if DEV_MODE else 'PROD'}')
# ---------------------------
# ConfigurationS
# ---------------------------
USE_FAKE_TEMPS = DEV_MODE
USE_FAKE_PRESSURE = DEV_MODE


# dicts for global variables
temperatures = {"current_temps" : [0,0,0,0]}
pressure = {"current_pressure" : 0, 'current_status': 0}




recording_start = time.time()

acq_event = threading.Event()
temp_event = threading.Event()
pressure_event = threading.Event()

temp_thread = threading.Thread(
    target=temperature_acquisition_thread,
    args=(USE_FAKE_TEMPS, temperatures, temp_event),
    daemon=True
)

pressure_thread = threading.Thread(
    target=pressure_acquisition_thread,
    args=(USE_FAKE_PRESSURE, pressure, pressure_event),
    daemon=True
)


temp_thread.start()
pressure_thread.start()


timestamps_buffer = []
temperatures_buffer = []
pressures_buffer = []

i = 0

try:
    start_time = time.time()
    while not acq_event.is_set():
        temps_snapshot = temperatures['current_temps']
        pressure_snapshot = pressure['current_pressure']
        
        tempString = f'{round(temps_snapshot[0], 2)}, {round(temps_snapshot[1], 2)}, {round(temps_snapshot[2], 2)}, {round(temps_snapshot[3], 2)}'
        pressureString = round(pressure_snapshot, 2)
        runtime = time.time() - start_time
        
        print(f'[{round(runtime, 1)}] Current temperatures: {tempString}, pressure: {pressureString}')
        
        temperatures_buffer.append(temps_snapshot)
        pressures_buffer.append(pressure_snapshot)
        timestamps_buffer.append(runtime)
        
        time.sleep(0.5)
finally:    
    save_data(temperatures=temperatures_buffer, pressures=pressures_buffer, timestamps=timestamps_buffer)
    acq_event.set()
    
    temp_event.set()
    temp_thread.join()
    
    pressure_event.set()
    pressure_thread.join()


