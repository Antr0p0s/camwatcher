import time
import threading
import queue
from resources.setBounds import get_manual_bubble_mask
from resources.tempWorker import temperature_acquisition_thread
from resources.pressureWorker import pressure_acquisition_thread
from resources.no_cam_workers import save_data
from resources.decreased.camworker import low_acquisition_thread
from resources.decreased.saveworker import save_buffer_worker
from resources.cam import PixelFlyCamera
import numpy as np
from resources.ui import LiveUI

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
AUTO_ENABLE_RECORDING = True
FPS_WINDOW = 20
CHUNK_SIZE = 200

# dicts for global variables
temperatures = {"current_temps" : [0,0,0,0]}
pressure = {"current_pressure" : 0, 'current_status': 0}
updates = {
    "total": 0,
    "saved": 0 ,
    "current_chunk_index": 0
}

FRAME_TIME = 1.0 / FPS_WINDOW

camera = PixelFlyCamera(frame_time=FRAME_TIME, exposure_time=0.1)

recording = True

print("[INIT] Please set bubble bounds...")
first_frame = None
while first_frame is None:
    init_frame = camera.get_latest_frame()
    if not init_frame is None:
        first_frame = init_frame
    else:
        time.sleep(0.1)

bounds, img_lims  = get_manual_bubble_mask(camera)

if len(bounds) == 2:
    exit()

x1, y1, x2, y2 = bounds
cropped_init_frame = np.array(first_frame)[y1:y2, x1:x2]

ui = LiveUI(cropped_init_frame, img_lims)

frame_queue = queue.Queue(maxsize=50)
timestamps_queue = queue.Queue(maxsize=50)

recording_start = time.time()

acq_event = threading.Event()
temp_event = threading.Event()
pressure_event = threading.Event()
chunk_event = threading.Event()
chunk_thread = None

acq_thread = threading.Thread(
    target=low_acquisition_thread,
    args=(camera, frame_queue, timestamps_queue, recording_start, bounds, acq_event),
    daemon=True
)

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

def toggle_recording(event):
    global recording, chunk_thread
    recording = not recording
    
    ui.btn_toggle.label.set_text(
        "Start recording" if not recording else "Stop recording"
    )
    print(f'toggling recording, current state: {recording}')

    if recording:
        # 1. Clear the stop event
        chunk_event.clear()
        #reset the buffers so the first file doesnt return 413
        frames_buffer.clear()
        timestamps_buffer.clear()
        temperatures_buffer.clear()
        pressures_buffer.clear()
        
        # 2. CREATE A NEW THREAD OBJECT
        chunk_thread = threading.Thread(
            target=save_buffer_worker,
            args=(frames_buffer, timestamps_buffer, temperatures_buffer, pressures_buffer, chunk_event, updates, CHUNK_SIZE),
            daemon=True
        )
        # 3. Start it
        chunk_thread.start()
        print("Recording started...")
    else:
        print("Recording stopped.")

ui.btn_toggle.on_clicked(toggle_recording)

temp_thread.start()
pressure_thread.start()
acq_thread.start()

timestamps_buffer = []
temperatures_buffer = []
pressures_buffer = []
frames_buffer = []

i = 0

try:
    last_image = cropped_init_frame  # initial frame

    while ui.exists() and not acq_event.is_set():
        t0 = time.time()
        got_frames = []
        got_frame = False
        got_timestamps = []
        got_timestamp = False
        current_temps = []

        while True:
            try:    
                # 1. Get the frame and timestamp
                frame_data = frame_queue.get_nowait()
                ts_data = timestamps_queue.get_nowait()
                
                # 2. Get the *current* temperature snapshot for this specific frame
                current_temp_snapshot = list(temperatures['current_temps']) # copy the list
                current_pressure_snapshot = pressure["current_pressure"]
                
                got_frames.append(frame_data)
                got_timestamps.append(ts_data)
                
                # 3. If recording, append all three synchronized pieces
                if recording:
                    frames_buffer.append(frame_data)
                    timestamps_buffer.append(ts_data)
                    temperatures_buffer.append(current_temp_snapshot) 
                    pressures_buffer.append(current_pressure_snapshot)
                elif current_pressure_snapshot < 100 and AUTO_ENABLE_RECORDING:
                    toggle_recording(1)
                                
                got_frame = True
                got_timestamp = True
            except queue.Empty as e:
                time.sleep(0.01)
                break
            except Exception as e:
                print(e)
                time.sleep(0.01)

        if got_frame and got_timestamp:
            last_image = got_frames[-1]
            # (Remove the .extend logic that was here previously)
            
            frame_timestamp = time.time() - recording_start
            ui.update_image(last_image)
            t1 = f'{temperatures["current_temps"][0]:0.1f}'
            t2 = f'{temperatures["current_temps"][1]:0.1f}'
            t3 = f'{temperatures["current_temps"][2]:0.1f}'
            t4 = f'{temperatures["current_temps"][3]:0.1f}'
            text1 = f'Time: {frame_timestamp:0.1f} - temps: {t1}, {t2}, {t3}, {t4}'
            text2 = f'Total frames: {updates['total']} (saved: {updates['saved']}) - index: {updates['current_chunk_index']}'
            text3 = f'Pressure: {(pressure["current_pressure"]):0.1f} mbar - status: {pressure['current_status']}'
            combined_text = f"{text2}\n{text1}\n{text3}"
            ui.set_sub_title(combined_text)
            ui.fig.canvas.flush_events()  # force immediate redraw
        else:
            time.sleep(0.05)
            continue

        # FPS calculation
        dt = time.time() - t0

        ui.set_title(f"Current filename: {ui.get_filename()}")

        sleep_time = FRAME_TIME - (time.time() - t0)
        if sleep_time > 0:
            time.sleep(sleep_time)

finally:
    acq_event.set()
    
    temp_event.set()
    temp_thread.join()
    
    pressure_event.set()
    pressure_thread.join()


