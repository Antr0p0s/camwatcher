import math
import time
from collections import deque

# Configuration
PORT = 'COM12'                  # Replace with your actual port
SUPPLY_VOLTS = 5.0
ANALOG_PIN_NUM = 0             # A0
MOV_AVG_LENGTH_VOLT = 1        # Smooths out analog signal noise

# =========================================================
# BACKENDS
# =========================================================

class ArduinoBackend:
    def __init__(self):
        from pyfirmata2 import Arduino
        self.Arduino = Arduino
        self.board = None
        self.analog_pin = None
        self.power_pin = None
        self._latest_value = None

    def connect(self, port):
        self.board = self.Arduino(port)
        
        self.power_pin = self.board.get_pin('d:2:o')
        
        # Turn ON the 5V power supply to your circuit
        self.power_pin.write(True)
        print("[VOLT] Arduino Power Pin (D2) set to HIGH (5V)")
        
        # Set up pin and attach asynchronous callback
        self.analog_pin = self.board.get_pin(f'a:{ANALOG_PIN_NUM}:r')
        self.analog_pin.register_callback(self._callback)
        self.analog_pin.enable_reporting()
        
        # Stream data from Arduino at maximum speed (approx every 19ms)
        # We will handle our own downsampling via the 40 FPS thread sleep.
        self.board.samplingOn()
        print(f"[VOLT] Arduino connected on {port}")

    def _callback(self, value):
        # Background thread from pyfirmata2 updates this raw float (0.0 to 1.0)
        self._latest_value = value

    def read_voltage(self):
        # Match standard structure: return converted physical voltage
        if self._latest_value is None:
            return None
        return self._latest_value * SUPPLY_VOLTS

    def close(self, port=None):
        print("[VOLT] Safely shutting down Arduino connection...")
        if self.board:
            try:
                if self.power_pin:
                    self.power_pin.write(False)
                    print("[VOLT] Arduino Power Pin (D2) set to LOW (0V)")
                # 1. Stop the analog pin from broadcasting data
                if self.analog_pin:
                    self.analog_pin.disable_reporting()
                
                # 2. Shut down the background sampling thread
                self.board.samplingOff()
                
                # 3. Give the thread a split second to spin down safely
                time.sleep(0.1) 
                
            except Exception as e:
                print(f"[VOLT] Error during thread spindown: {e}")
            finally:
                # 4. Finally, release the serial port
                self.board.exit()
                
        print("[VOLT] Arduino connection closed cleanly.")

class FakeArduinoBackend:
    def __init__(self):
        self.start_time = time.time()

    def connect(self, port):
        print("[VOLT] Fake Arduino backend connected (simulation mode)")

    def read_voltage(self):
        """ Simulates a fluctuating DC voltage reading """
        t = time.time() - self.start_time
        # Generates a wave fluctuating around 2.5V with minor noise
        base_volt = 2.5 + 1.2 * math.sin(t / 15)
        noise = math.sin(t * 10) * 0.02
        return max(0.0, min(SUPPLY_VOLTS, base_volt + noise))

    def close(self, port=None):
        print("[VOLT] Fake Arduino backend closed")


# =========================================================
# AUTO BACKEND SELECTOR
# =========================================================
def get_voltage_backend(USE_FAKE_VOLTS):
    if USE_FAKE_VOLTS:
        return FakeArduinoBackend()
    try:
        return ArduinoBackend()
    except Exception as e:
        raise RuntimeError(f"No Arduino backend available: {e}")


# =========================================================
# MAIN THREAD WORKER
# =========================================================
def voltage_acquisition_thread(USE_FAKE_VOLTS, voltages, recording_start, stop_event):
    """
    Expects 'voltages' to be a dict pre-initialized on the main thread:
    voltages = {
        'current_volt': 0.0,
        'full_volts': [],
        'full_timestamps': []
    }
    """
    print("[VOLT] Voltage thread started.")

    backend = get_voltage_backend(USE_FAKE_VOLTS)
    backend.connect(PORT)

    history = deque(maxlen=MOV_AVG_LENGTH_VOLT)

    try:
        while not stop_event.is_set():
            try:
                raw_voltage = backend.read_voltage()
                
                # Handle startup delay where pyfirmata has not received packets yet
                if raw_voltage is None:
                    time.sleep(1 / 20)
                    continue

                history.append(raw_voltage)

                # Store data in shared dict structures matching temp thread design
                voltages["current_volt"] = raw_voltage
                voltages['full_volts'].append(raw_voltage)
                voltages['full_timestamps'].append(time.time() - recording_start)

            except Exception as e:
                print(f"[VOLT] Runtime error: {e}")
                voltages["current_volt"] = -1.0 # Error flag state

            time.sleep(1 / 40) # Match your 40 FPS sample loop

    except Exception as e:
        print(f"[VOLT] Error: {e}")
        voltages["current_volt"] = -1.0
        
        for _ in range(5):
            if stop_event.is_set():
                break
            time.sleep(0.005)

    finally:
        backend.close()
        print("[VOLT] Voltage thread stopped.")