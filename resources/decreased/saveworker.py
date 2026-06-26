import os
from datetime import datetime
import time
import numpy as np

from dotenv import load_dotenv
import os

load_dotenv()

NO_CAM_SAVE_LOC = os.getenv("NO_CAM_SAVE_LOC")

def save_buffer_worker(frames_buffer, timestamps_buffer, temperatures_buffer, raw_temperatures_buffer,
                       pressures_buffer, stop_event, updates, chunk_size, chunk_name, vms_buffer,
                       full_raw_temps_buffer, full_timestamps_buffer, full_volts_buffer, full_volt_timestamps_buffer, volts_buffer):
    chunk_counter = 1
    chunk_dir = f'{NO_CAM_SAVE_LOC}/{chunk_name}' if 'prct' not in chunk_name else f'{NO_CAM_SAVE_LOC}/chunks/{datetime.now().strftime('%m-%d-%H-%M')}'

    os.makedirs(chunk_dir, exist_ok=True)

    print("[Save worker] Save worker started")

    while not stop_event.is_set():
        updates['total'] = updates['saved'] + len(frames_buffer)
        if len(frames_buffer) > chunk_size:
            frames_raw = frames_buffer.copy()
            times_raw = timestamps_buffer.copy()
            temps_raw = temperatures_buffer.copy()
            raw_temps_raw = raw_temperatures_buffer.copy()
            press_raw = pressures_buffer.copy()
            vms_raw = vms_buffer.copy()
            full_raw_temps = full_raw_temps_buffer.copy()
            full_timestamps = full_timestamps_buffer.copy()
            full_volts = full_volts_buffer.copy()
            full_volts_times = full_volt_timestamps_buffer.copy()
            volts_raw = volts_buffer.copy()
                
            frames_buffer.clear()
            timestamps_buffer.clear()
            temperatures_buffer.clear()
            raw_temperatures_buffer.clear()
            pressures_buffer.clear()
            vms_buffer.clear()
            full_raw_temps_buffer.clear()
            full_timestamps_buffer.clear()
            full_volts_buffer.clear()
            full_volt_timestamps_buffer.clear()
            volts_buffer.clear()

            
            filename = f"{chunk_dir}/chunk_{chunk_counter}.npz"
            updates['saved']+= len(frames_raw)
            updates['current_chunk_index'] = chunk_counter

            chunk_counter+= 1

            np.savez(
                filename,
                frames=np.array(frames_raw, dtype=np.float16),
                timestamps=np.array(times_raw, dtype=np.float16),
                temperatures=np.array(temps_raw, dtype=np.float16),
                raw_temperatures=np.array(raw_temps_raw, dtype=np.float16),
                pressures=np.array(press_raw, dtype=np.float16),
                full_raw_temps=np.array(full_raw_temps, dtype=np.float16),
                full_timestamps=np.array(full_timestamps, dtype=np.float16),
                full_volts=np.array(full_volts, dtype=np.float16),
                full_volts_times=np.array(full_volts_times, dtype=np.float16),
                volts_raw=np.array(volts_raw, dtype=np.float16),
                vms=np.array(vms_raw, dtype=np.float16)
            )
        else:
            time.sleep(0.1)

    filename = f"{chunk_dir}/chunk_{chunk_counter}.npz"
    frames_raw = frames_buffer.copy()
    times_raw = timestamps_buffer.copy()
    temps_raw = temperatures_buffer.copy()
    press_raw = pressures_buffer.copy()
    raw_temps_raw = raw_temperatures_buffer.copy()
    vms_raw = vms_buffer.copy()
    full_raw_temps = full_raw_temps_buffer.copy()
    full_timestamps = full_timestamps_buffer.copy()
    full_volts = full_volts_buffer.copy()
    full_volts_times = full_volt_timestamps_buffer.copy()
    volts_raw = volts_buffer.copy()
    
    np.savez(
        filename,
        frames=np.array(frames_raw, dtype=np.float16),
        timestamps=np.array(times_raw, dtype=np.float16),
        temperatures=np.array(temps_raw, dtype=np.float16),
        raw_temperatures=np.array(raw_temps_raw, dtype=np.float16),
        pressures=np.array(press_raw, dtype=np.float16),
        full_raw_temps=np.array(full_raw_temps, dtype=np.float16),
        full_timestamps=np.array(full_timestamps, dtype=np.float16),
        full_volts=np.array(full_volts, dtype=np.float16),
        full_volts_times=np.array(full_volts_times, dtype=np.float16),
        volts_raw=np.array(volts_raw, dtype=np.float16),
        vms=np.array(vms_raw, dtype=np.float16)
    )
    print("[DISPATCHER] Stopped")