import numpy as np
import os
import time
import random

class FakePixelFlyCamera:
    def __init__(self, frame_time=1.0, exposure_time=0.005, fifo_size=1000):
        # The time the "camera" was turned on
        self.start_time = time.time()
        self.exposure_time = exposure_time
        self.frame_time = frame_time
        self.previous_chunk = -1
        
        # This acts as the internal memory of the camera
        self.internal_memory = []

    def grab_frames(self, n=10):
        """
        Calculates how many seconds have passed, loads the corresponding chunk,
        converts it to a raw list, and clears the memory.
        """
        # 1. Determine which file to load based on elapsed time
        elapsed_seconds = int((time.time() - self.start_time) / 10)
        
        if elapsed_seconds == self.previous_chunk:
            return []
        
        # Formatting to match your chunk_0000.npy naming convention
        file_name = f'chunk_{elapsed_seconds:04d}.npy'
        file_path = os.path.join('./data', file_name)

        if os.path.exists(file_path):
            # Load the numpy array
            arr = np.load(file_path)
            return arr.tolist()
    
    def close(self):
        print('Closing fake camera')
        
def getRandomTemperature():
    return random.random()*20