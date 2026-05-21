import os
import time
import numpy as np
import requests
import io
import queue
from dotenv import load_dotenv

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

def get_oldest_chunk_file(temp_dir="./temp"):
    files = [f for f in os.listdir(temp_dir) if f.startswith("chunk_") and f.endswith(".npz")]
    if not files:
        return None

    # sort by chunk index
    files.sort(key=lambda x: int(x.split("_")[1].split(".")[0]))
    return os.path.join(temp_dir, files[0])

def temp_has_files(temp_dir="./temp"):
    return any(
        f.startswith("chunk_") and f.endswith(".npz")
        for f in os.listdir(temp_dir)
    )

def save_buffer_worker(frames_buffer, timestamps_buffer, temperatures_buffer, raw_temperatures_buffer, pressures_buffer,
                       stop_event, max_buffer, api_url, ui, recording,
                       upload_workers_status, vms_buffer):

    global chunk_counter, latest_data

    os.makedirs("./temp", exist_ok=True)

    print("[DISPATCHER] Started")

    while not stop_event.is_set() or len(frames_buffer) > 0:
        # 🔥 1. PRIORITY: send oldest disk chunk if worker available
        if 0 in upload_workers_status:
            oldest = get_oldest_chunk_file()
            if oldest is not None:
                try:
                    idx = int(
                        os.path.basename(oldest)
                        .split("_")[1]
                        .split(".")[0]
                    )
                    upload_queue.put((api_url, idx, oldest), timeout=0.1)
                except queue.Full:
                    pass
                continue
        # 🔥 2. Process RAM buffer
        if len(frames_buffer) >= max_buffer or (stop_event.is_set() and len(frames_buffer) > 0 or temp_has_files()):
            frames_raw = frames_buffer.copy()
            times_raw = timestamps_buffer.copy()
            temps_raw = temperatures_buffer.copy()
            raw_temps_raw = raw_temperatures_buffer.copy()
            press_raw = pressures_buffer.copy()
            vms_raw = vms_buffer.copy()

            frames_buffer.clear()
            timestamps_buffer.clear()
            temperatures_buffer.clear()
            raw_temperatures_buffer.clear()
            pressures_buffer.clear()
            vms_buffer.clear()

            latest_data['total_frames'] += len(frames_raw)

            if recording:
                for i in range(0, len(frames_raw), max_buffer):
                    chunk_frames = frames_raw[i:i+max_buffer]
                    chunk_times = times_raw[i:i+max_buffer]
                    chunk_temps = temps_raw[i:i+max_buffer]
                    chunk_raw_temps = raw_temps_raw[i:i+max_buffer]
                    chunk_press = press_raw[i:i+max_buffer]
                    chunk_vms = vms_raw[i:i+max_buffer]

                    chunk_idx = chunk_counter
                    chunk_counter += 1

                    # 🚀 If worker available → send directly (NO disk)
                    if 0 in upload_workers_status:
                        upload_queue.put((
                            api_url,
                            chunk_idx,
                            chunk_frames,
                            chunk_times,
                            chunk_temps,
                            chunk_raw_temps,
                            chunk_press,
                            chunk_vms,
                            ui.get_img_lims()
                        ))

                    # 💾 Otherwise → write to disk
                    else:
                        filename = f"./temp/chunk_{chunk_idx}.npz"

                        np.savez(
                            filename,
                            frames=np.array(chunk_frames, dtype=np.float16),
                            timestamps=np.array(chunk_times, dtype=np.float16),
                            temperatures=np.array(chunk_temps, dtype=np.float16),
                            raw_temperatures=np.array(chunk_raw_temps, dtype=np.float16),
                            pressures=np.array(chunk_press, dtype=np.float16),
                            vms=np.array(chunk_vms, dtype=np.float16),
                            img_min=np.array([ui.get_img_lims()[0]]),
                            img_max=np.array([ui.get_img_lims()[1]])
                        )

        else:
            if len(frames_buffer) == 0 and temp_has_files():
                time.sleep(0.5)
            else:
                time.sleep(0.05)

    print("[DISPATCHER] Stopped")

def upload_worker(worker, upload_workers_status, updates):
    global latest_data
    session = requests.Session()

    while True:
        item = upload_queue.get()
        if item is None:
            break

        upload_workers_status[worker] = 1

        # Detect mode
        if len(item) == 3:
            # 💾 Disk mode
            api_url, chunk_idx, filename = item

            with open(filename, "rb") as f:
                buffer = io.BytesIO(f.read())

            with np.load(filename) as data:
                n_chunks = data["frames"].shape[0]

            delete_after = True

        else:
            # 🚀 RAM mode
            api_url, chunk_idx, frames, timestamps, temps, raw_temps, pressures, vms, img_lims = item

            buffer = io.BytesIO()
            frames_data = np.array(frames, dtype=np.float16)

            np.savez(buffer,
                    frames=frames_data,
                    timestamps=np.array(timestamps, dtype=np.float16),
                    temperatures=np.array(temps, dtype=np.float16),
                    raw_temperatures=np.array(raw_temps, dtype=np.float16),
                    pressures=np.array(pressures, dtype=np.float16),
                    vms=np.array(vms, dtype=np.float16),
                    img_min=np.array([img_lims[0]]),
                    img_max=np.array([img_lims[1]]))

            n_chunks = frames_data.shape[0]
            delete_after = False
        latest_data['frames_uploaded'] += n_chunks 
        
        print(f"[UPLOADER {worker + 1}] Uploading chunk {chunk_idx} (frames: {n_chunks}, frames uploaded: {latest_data['frames_uploaded']} out of {latest_data['total_frames']}, using {sum(upload_workers_status)}/{len(upload_workers_status)} upload threads)")

        success = False
        # Try up to 3 times before giving up and skipping
        for attempt in range(2):
            try:
                buffer.seek(0)  # CRITICAL: Reset pointer for EVERY attempt
                files = {"file": (f"chunk_{chunk_idx}.npz", buffer, "application/octet-stream")}
                
                response = session.post(
                    f"{api_url}/upload_data",
                    files=files,
                    headers=headers,
                    data={"chunk_index": chunk_idx},
                    timeout=120
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
            print(f"[UPLOADER {worker}] PERMANENT FAILURE for chunk {chunk_idx}. Skipping {n_chunks} frames.")
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
        if delete_after:
            try:
                os.remove(filename)
            except:
                pass
        upload_queue.task_done()