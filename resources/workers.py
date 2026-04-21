import os
import threading
import time
import numpy as np
import requests
import io
import queue
from dotenv import load_dotenv
import json
from concurrent.futures import ThreadPoolExecutor


upload_queue = queue.Queue(maxsize=100)

latest_data = {
    'frames_uploaded': 0,
    'total_frames': 0,
    'skipped_chunks': 0
}

chunk_counter = 0


load_dotenv()
AUTH_KEY = os.getenv("API_AUTH_KEY")

headers = {"Authorization": f"Bearer {AUTH_KEY}"}

def acquisition_thread(camera, frame_queue, timestamps_queue, recording_start, bounds, stop_event):
    """
    Acquires frames and crops them to bounds immediately to save memory and CPU.
    bounds: (x_min, y_min, x_max, y_max)
    """
    frame_count = 0

    x1, y1, x2, y2 = bounds

    while not stop_event.is_set():
        frame = camera.get_latest_frame()

        if frame is None:
            time.sleep(0.001) 
            continue
        
        frame = np.array(frame)
        proc_frame = frame[y1:y2, x1:x2]
        try:
            frame_queue.put_nowait(proc_frame)
            timestamps_queue.put_nowait(time.time() - recording_start)    
        except queue.Full:
            pass  # drop frames if GUI can't keep up
        
        frame_count += 1
            
    print("[ACQ] Acquisition thread stopped.")
    

chunk_counter = 0
latest_data = {
    'frames_uploaded': 0,
    "total_frames": 0
}

def save_buffer_worker(frames_buffer, timestamps_buffer, temperatures_buffer, pressures_buffer,
                       stop_event, max_buffer, api_url, ui, recording):

    global chunk_counter, latest_data

    print("[UPLOADER] Dispatcher started")

    while not stop_event.is_set() or len(frames_buffer) > 0:

        if len(frames_buffer) >= max_buffer or (stop_event.is_set() and len(frames_buffer) > 0):

            # snapshot (fast shallow copy)
            frames_raw = frames_buffer.copy()
            times_raw = timestamps_buffer.copy()
            temps_raw = temperatures_buffer.copy()
            press_raw = pressures_buffer.copy()

            frames_buffer.clear()
            timestamps_buffer.clear()
            temperatures_buffer.clear()
            pressures_buffer.clear()

            frames_data = np.array(frames_raw, dtype=np.float16)

            latest_data['total_frames'] += frames_data.shape[0]

            # split into chunks
            if recording:
                for i in range(0, len(frames_raw), max_buffer):

                    upload_queue.put((
                        api_url,
                        chunk_counter,
                        frames_raw[i:i+max_buffer],
                        times_raw[i:i+max_buffer],
                        temps_raw[i:i+max_buffer],
                        press_raw[i:i+max_buffer],
                        ui.get_img_lims()
                    ))

                    chunk_counter += 1

        else:
            time.sleep(0.2)

    print("[UPLOADER] Dispatcher stopped")

def upload_worker(worker, upload_workers_status, updates):
    global latest_data
    session = requests.Session()

    while True:
        item = upload_queue.get()
        if item is None: break

        api_url, chunk_idx, frames, timestamps, temps, pressures, img_lims = item
        upload_workers_status[worker] = 1
        
        # Prepare the binary data once
        buffer = io.BytesIO()
        frames_data = np.array(frames, dtype=np.float16)
        np.savez(buffer, 
                 frames=frames_data, 
                 timestamps=np.array(timestamps, dtype=np.float16),
                 temperatures=np.array(temps, dtype=np.float16),
                 pressures=np.array(pressures, dtype=np.float16),
                 img_min=np.array([img_lims[0]]), 
                 img_max=np.array([img_lims[1]]))
        
        latest_data['frames_uploaded'] += frames_data.shape[0] 
        
        print(f"[UPLOADER {worker + 1}] Uploading chunk {chunk_idx} (frames uploaded: {latest_data['frames_uploaded']} out of {latest_data['total_frames']}, using {sum(upload_workers_status)}/{len(upload_workers_status)} upload threads)")

        success = False
        # Try up to 3 times before giving up and skipping
        for attempt in range(3):
            try:
                buffer.seek(0)  # CRITICAL: Reset pointer for EVERY attempt
                files = {"file": (f"chunk_{chunk_idx}.npz", buffer, "application/octet-stream")}
                
                response = session.post(
                    f"{api_url}/upload_data",
                    files=files,
                    headers=headers,
                    data={"chunk_index": chunk_idx},
                    timeout=30 if attempt > 0 else 60
                )

                if response.status_code == 200:
                    res = response.json()
                    updates['total'] = res.get('total_count', 0)
                    updates['current_rendered'] = res.get('current_rendered', 0)
                    success = True
                    break # Out of the retry loop
                else:
                    print(f"[UPLOADER {worker}] Attempt {attempt+1} on chunk {chunk_idx} failed: {response.status_code}")
                    time.sleep(1) # Small backoff
            except Exception as e:
                print(f"[UPLOADER {worker}] Connection error on chunk {chunk_idx} attempt {attempt+1}: {e}")
                time.sleep(1)

        if not success:
            print(f"[UPLOADER {worker}] PERMANENT FAILURE for chunk {chunk_idx}. Skipping.")
            try:
                # Use a specific timeout for skip to ensure it actually hits
                session.post(f"{api_url}/skip_chunk", 
                             data={'chunk_index': chunk_idx}, 
                             headers=headers, 
                             timeout=10)
                updates['skipped_chunks'] += 1
            except:
                print(f"[UPLOADER {worker}] Could not even send SKIP command for {chunk_idx}")

        upload_workers_status[worker] = 0
        print(f"[UPLOADER {worker + 1}] Uploaded chunk {chunk_idx}")
        upload_queue.task_done()