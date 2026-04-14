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


load_dotenv()
AUTH_KEY = os.getenv("API_AUTH_KEY")

headers = {"Authorization": f"Bearer {AUTH_KEY}"}

def acquisition_thread(camera, frame_queue, timestamps_queue, recording_start, bounds, stop_event):
    """
    Acquires frames and crops them to bounds immediately to save memory and CPU.
    bounds: (x_min, y_min, x_max, y_max)
    """
    frame_count = 0
    t0 = time.perf_counter()

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

        # Print FPS every second
        now = time.perf_counter()
        if now - t0 >= 1.0:
            fps = frame_count / (now - t0)
            print(f"[ACQ] Camera FPS ≈ {fps:.1f}")
            frame_count = 0
            t0 = now
            
    print("[ACQ] Acquisition thread stopped.")
    

chunk_counter = 0

def save_buffer_worker(frames_buffer, timestamps_buffer, temperatures_buffer, pressures_buffer, stop_event, updates, max_buffer, api_url, ui, recording):
    global finalising
    buffer_lock = threading.Lock()
    global chunk_counter
    chunk_counter = 0
    MAX_SUB_CHUNK = 10 

    # Use a ThreadPool to allow multiple simultaneous uploads
    # 4 workers is usually plenty to saturate a connection without overwhelming it
    with ThreadPoolExecutor(max_workers=6) as executor:
        while not stop_event.is_set() or len(frames_buffer) > 0:
            if len(frames_buffer) >= max_buffer or (stop_event.is_set() and len(frames_buffer) > 0):
                with buffer_lock:
                    frames_raw = list(frames_buffer)
                    times_raw = list(timestamps_buffer)
                    temps_raw = list(temperatures_buffer)
                    pressures_raw = list(pressures_buffer)
                    
                    frames_buffer.clear()
                    timestamps_buffer.clear()
                    temperatures_buffer.clear()
                    pressures_buffer.clear()

                # Slice and dispatch to the thread pool
                for i in range(0, len(frames_raw), MAX_SUB_CHUNK):
                    end = i + MAX_SUB_CHUNK
                    
                    # .submit() is non-blocking; it returns immediately
                    if recording:
                        img_lims = ui.get_img_lims()
                        
                        executor.submit(
                            perform_chunk_upload, 
                            api_url, headers, updates, chunk_counter,
                            frames_raw[i:end], 
                            times_raw[i:end], 
                            temps_raw[i:end],
                            pressures_raw[i:end],
                            img_lims
                        )
                        chunk_counter += 1
            
            if not stop_event.is_set():
                time.sleep(0.5)
        
        # When the 'with' block ends, it automatically waits for all remaining 
        # uploads to finish. Because they are parallel, this will be much faster.
        remaining_chunks_amount = round(len(frames_raw)/MAX_SUB_CHUNK)
        if remaining_chunks_amount > 0:
            print(f'[WORKER] Not uploading {remaining_chunks_amount} chunk(s) as the program is terminated')

def perform_chunk_upload(api_url, headers, updates, chunk_idx, data_list, timestamps, temperatures, pressures, img_lims):
    arr = np.array(data_list, dtype=np.float32)
    buffer = io.BytesIO()
    np.save(buffer, arr)
    buffer.seek(0)
    global chunk_counter

    try:
        files = {"file": (f"chunk_{chunk_idx}.npy", buffer, "application/octet-stream")}
        # Added chunk_index to the form data
        
        print(f'Uploading {len(timestamps)} frames')

        data = {
            "img_min": float(img_lims[0]),
            "img_max": float(img_lims[1]),
            "chunk_index": chunk_idx,
            "timestamps": json.dumps(timestamps),
            "temperatures": json.dumps(temperatures),
            "pressures": json.dumps(pressures)
        }
        
        # if chunk_idx % 10 == 9:
        #     from ssl import SSLEOFError
        #     # We mimic the exact error structure you saw
        #     ssl_err = SSLEOFError(8, 'EOF occurred in violation of protocol (_ssl.c:2406)')
        #     raise requests.exceptions.SSLError(f"Max retries exceeded (Caused by {ssl_err})")
        # # -------------------------------
        
        response = requests.post(f'{api_url}/upload_data', files=files, data=data, headers=headers, timeout=60)
        
        if response.status_code == 200:
            res_dict = response.json()
            if res_dict.get('status') == 'success':
                updates['total'] = res_dict['total_count']
                updates['current_rendered'] = res_dict['current_rendered']
                updates['ignored_temps'] += res_dict.get('ignored_temps', 0)
        else:
            print(f"[UPLOADER] 413 or Error: {response.status_code}")
            requests.post(f'{api_url}/skip_chunk', data={'chunk_index': chunk_idx}, headers=headers)
    except Exception as e:
        print(f"[UPLOADER] Hard Failure on {chunk_idx}: {e}")
        # Send a tiny 'SKIP' packet to the server so it increments next_expected_index
        requests.post(f'{api_url}/skip_chunk', data={'chunk_index': chunk_idx}, headers=headers)
        
