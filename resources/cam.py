import time
import pco
import numpy as np

class PixelFlyCamera:
    def __init__(self, frame_time, exposure_time=0.005, fifo_size=1000):
        self.frame_time = frame_time
        self.cam = pco.Camera()
        self.cam.default_configuration()
        self.cam.auto_exposure_off()
        # "fifo" mode is essential for ring buffer behavior
        self.cam.record(mode="fifo", number_of_images=fifo_size)
        self.cam.exposure_time = exposure_time

        self.last_frame_index = -1  # Track the last seen frame ID
        self.latest_index = -1

        # Warm up/Wait for the first frame to establish shape
        while True:
            try:
                # Request the most recent frame (index -1 or 0xffffffff)
                image, meta = self.cam.image(0xffffffff)
                self.image_shape = image.shape
                # We don't update last_frame_index here yet, 
                # so the first call to get_latest_frame succeeds.
                break
            except (pco.camera_exception.CameraException, RuntimeError):
                time.sleep(0.001)

    def get_latest_frame(self):
        """
        Returns the most recent frame from the camera.
        Returns None if no new frame has been captured since the last call.
        """
        try:
            # image_number=0xffffffff grabs the newest image in the buffer
            image, meta = self.cam.image()
            if image is None:
                return None
        
            self.latest_index += 1

            # If the index hasn't changed, we've already seen this frame
            if self.latest_index == self.last_frame_index:
                return None

            # Update our tracker and return the new data
            self.last_frame_index = self.latest_index
            return image.astype(np.float16)

        except (pco.camera_exception.CameraException, RuntimeError):
            # No image available yet or camera busy
            return None

    def close(self):
        self.cam.stop()
        self.cam.close()