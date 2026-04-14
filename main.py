import time
import queue
import threading
import numpy as np
from collections import deque

from resources.cam import PixelFlyCamera
from resources.ui import LiveUI
from resources.workers import acquisition_thread, save_buffer_worker
from resources.tempWorker import temperature_acquisition_thread
from resources.pressureWorker import pressure_acquisition_thread
from resources.apiHandling import trigger_server_compilation, cleanup_server, ping_api
from resources.setBounds import get_manual_bubble_mask

DEV_MODE = True
# ---------------------------
# Configuration
# ---------------------------
VIDEO_FPS = 15 # FPS used in the final video
MAX_BUFFER = 5 # memory - then it gets uploaded to the server mostly to keep under the cloudflare 50MB limit
FPS_WINDOW = 20 #FPS for the window
FORCE_BACKUP = True
USE_FAKE_TEMPS = DEV_MODE
USE_FAKE_PRESSURE = DEV_MODE
AUTO_ENABLE_RECORDING = False #not DEV_MODE

# 
# [UPLOADER] Hard Failure on 2293: HTTPSConnectionPool(host='stage.randomwebserver.eu', port=443): Max retries exceeded with url: /upload_data (Caused by SSLError(SSLEOFError(8, 'EOF occurred in violation of protocol (_ssl.c:2406)')))
# [UPLOADER] Hard Failure on 2296: HTTPSConnectionPool(host='stage.randomwebserver.eu', port=443): Max retries exceeded with url: /upload_data (Caused by SSLError(SSLEOFError(8, 'EOF occurred in violation of protocol (_ssl.c:2406)')))
# 
# ---------------------------
# State
# ---------------------------
recording = False
FRAME_TIME = 1.0 / FPS_WINDOW
API_URL = 'http://127.0.0.1:8000/' if DEV_MODE else "https://stage.randomwebserver.eu"
API_URL = "https://stage.randomwebserver.eu"

if not ping_api(API_URL):
    raise LookupError('Server not online')

cleanup_server(API_URL)

# load the camera
camera = PixelFlyCamera(frame_time=FRAME_TIME, exposure_time=0.02)

# dicts for global variables
temperatures = {"current_temps" : [0,0,0,0,0]}
pressure = {"current_pressure" : 0, 'current_status': 0}

# dict to get the latest updates
updates = {
    "total": 0,
    "ignored_temps": 0 ,
    "current_rendered": 0
}

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

# ---------------------------
# Acquisition thread
# ---------------------------
frame_queue = queue.Queue(maxsize=50)
timestamps_queue = queue.Queue(maxsize=50)

recording_start = time.time()

acq_event = threading.Event()
temp_event = threading.Event()
pressure_event = threading.Event()

acq_thread = threading.Thread(
    target=acquisition_thread,
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

acq_thread.start()
temp_thread.start()
pressure_thread.start()

# Initialize LiveUI
ui = LiveUI(cropped_init_frame, img_lims)

frames_buffer = []
timestamps_buffer = []
temperatures_buffer = []
pressures_buffer = []
# ---------------------------
# Button callbacks
# ---------------------------
# Create the event globally so we can signal the thread to stop
chunk_event = threading.Event()
chunk_thread = None # Placeholder

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
        
        # 2. CREATE A NEW THREAD OBJECT
        chunk_thread = threading.Thread(
            target=save_buffer_worker,
            args=(frames_buffer, timestamps_buffer, temperatures_buffer, pressures_buffer, chunk_event, updates, MAX_BUFFER, API_URL, ui, recording),
            daemon=True
        )
        # 3. Start it
        chunk_thread.start()
        print("Recording started...")
    else:
        print("Recording stopped.")

ui.btn_toggle.on_clicked(toggle_recording)

# ---------------------------
# Main loop
# ---------------------------

frame_times = deque(maxlen=FPS_WINDOW)  # rolling FPS

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
                    # FIX: Use append() so it's one list entry per frame
                    temperatures_buffer.append(current_temp_snapshot) 
                    pressures_buffer.append(current_pressure_snapshot)
                    # temp for easy testing
                elif current_pressure_snapshot < 1000 and AUTO_ENABLE_RECORDING:
                    toggle_recording(1)
                
                got_frame = True
                got_timestamp = True
            except queue.Empty:
                break

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
            text2 = f'Total frames: {updates['total']} (rendered: {updates['current_rendered']}) - ignored temps: {updates['ignored_temps']}'
            text3 = f'Pressure: {(pressure["current_pressure"]):0.1f} mbar - status: {pressure['current_status']}'
            combined_text = f"{text2}\n{text1}\n{text3}"
            ui.set_sub_title(combined_text)
            ui.fig.canvas.flush_events()  # force immediate redraw
        else:
            time.sleep(0.001)
            continue

        # FPS calculation
        dt = time.time() - t0
        frame_times.append(dt)
        fps = 1.0 / (sum(frame_times)/len(frame_times) + 1e-6)

        ui.set_title(f"Display FPS ≈ {fps:.1f} | Current filename: {ui.get_filename()}")

        sleep_time = FRAME_TIME - (time.time() - t0)
        if sleep_time > 0:
            time.sleep(sleep_time)

finally:
    camera.close()
    ui.close()

    acq_event.set()
    acq_thread.join()
    
    temp_event.set()
    temp_thread.join()
    
    pressure_event.set()
    pressure_thread.join()
    
    chunk_event.set()
    chunk_thread.join()

    filename = ui.get_filename()
    success_mp4 = trigger_server_compilation(API_URL, FORCE_BACKUP, DEV_MODE, filename)
    # cleanup_server(API_URL)


