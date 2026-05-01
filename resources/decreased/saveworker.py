import os
from datetime import datetime
import time
import numpy as np

def save_buffer_worker(frames_buffer, timestamps_buffer, temperatures_buffer, 
                       pressures_buffer, stop_event, updates, chunk_size, chunk_name):
    chunk_counter = 1
    chunk_dir = f'./data/chunks/{chunk_name}' if 'prct' not in chunk_name else f'./data/chunks/{datetime.now().strftime('%m-%d-%H-%M')}'

    os.makedirs(chunk_dir, exist_ok=True)

    print("[Save worker] Save worker started")

    while not stop_event.is_set():
        updates['total'] = updates['saved'] + len(frames_buffer)
        if len(frames_buffer) > chunk_size:
            frames_raw = frames_buffer.copy()
            times_raw = timestamps_buffer.copy()
            temps_raw = temperatures_buffer.copy()
            press_raw = pressures_buffer.copy()

            frames_buffer.clear()
            timestamps_buffer.clear()
            temperatures_buffer.clear()
            pressures_buffer.clear()
            
            filename = f"{chunk_dir}/chunk_{chunk_counter}.npz"
            updates['saved']+= len(frames_raw)
            updates['current_chunk_index'] = chunk_counter

            chunk_counter+= 1

            np.savez(
                filename,
                frames=np.array(frames_raw, dtype=np.float16),
                timestamps=np.array(times_raw, dtype=np.float16),
                temperatures=np.array(temps_raw, dtype=np.float16),
                pressures=np.array(press_raw, dtype=np.float16)
            )
        else:
            time.sleep(0.1)


    print("[DISPATCHER] Stopped")