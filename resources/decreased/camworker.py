import time
import queue
import numpy as np

def low_acquisition_thread(camera, frame_queue, timestamps_queue, recording_start, bounds, stop_event):
    print('[ACQ] Low intensity acquisiton thread started')
    frame_count = 0

    x1, y1, x2, y2 = bounds

    while not stop_event.is_set():
        frame = camera.get_latest_frame()

        if frame is None:
            time.sleep(0.05) 
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