import math
import time
from collections import deque

BOARD_NUM = 0
OFFSETS = [0, -24.501, -42.082, -16.723] # blue, black, red, white
COEFFICIENTS = [0, 2.108, 2.8839, 1.6371]
PROBE_ORDER=[0, 1, 3, 2] 
NUM_PROBES = 4


def convert_temperature(measured_temp, probe_no):
    probe = PROBE_ORDER[probe_no]
    
    if probe ==  0: # blue
        return (5.2213 * 10^-4) * math.exp(0.52389 * measured_temp)
    return COEFFICIENTS[probe] * measured_temp + OFFSETS[probe]

class MCCBackend:
    def __init__(self):
        from mcculw import ul
        from mcculw.enums import InterfaceType, TempScale
        from mcculw.ul import ULError

        self.ul = ul
        self.InterfaceType = InterfaceType
        self.TempScale = TempScale
        self.ULError = ULError

        self.device = None

    def connect(self, board_num):
        devices = self.ul.get_daq_device_inventory(self.InterfaceType.ETHERNET)
        if not devices:
            raise RuntimeError("No MCC Ethernet devices found")

        self.device = devices[0]

        try:
            self.ul.create_daq_device(board_num, self.device)
        except self.ULError:
            self.ul.release_daq_device(board_num)
            self.ul.create_daq_device(board_num, self.device)

        print(f"[TEMP] Windows MCC connected: {self.device.product_name}")

    def read_temp(self, board_num, channel):
        return self.ul.t_in(board_num, channel, self.TempScale.CELSIUS)

    def close(self, board_num):
        self.ul.release_daq_device(board_num)

class FakeBackend:
    def __init__(self):
        self.start_time = time.time()

    def connect(self, board_num):
        print("[TEMP] Fake backend connected (simulation mode)")

    def read_temp(self, board_num, channel):
        """
        Simulates thermocouple readings with:
        - slow drift
        - channel offset differences
        - small noise
        """
        t = time.time() - self.start_time

        # base temperature (room temp drift)
        base = 22 + 2 * math.sin(t / 30)

        # each channel behaves slightly differently
        channel_offset = channel * 0.8

        # small simulated noise
        noise = math.sin(t * (channel + 1)) * 0.15

        return base + channel_offset + noise

    def close(self, board_num):
        print("[TEMP] Fake backend closed")


# =========================================================
# AUTO BACKEND SELECTOR
# =========================================================
def get_backend(USE_FAKE_TEMPS):
    if USE_FAKE_TEMPS:
        return FakeBackend()
    try:
        # Try Windows first
        return MCCBackend()
    
    except NameError:
        raise RuntimeError(
            "No DAQ backend available (mcculw or uldaq missing)"
        )


# =========================================================
# MAIN THREAD
# =========================================================
def temperature_acquisition_thread(USE_FAKE_TEMPS, temperatures, stop_event):
    print("[TEMP] Temperature thread started.")

    backend = get_backend(USE_FAKE_TEMPS)
    backend.connect(BOARD_NUM)

    history = [deque(maxlen=5) for _ in range(NUM_PROBES)]

    try:
        while not stop_event.is_set():
            current_temps = [0] * NUM_PROBES

            for i in range(NUM_PROBES):
                try:
                    probe_num = PROBE_ORDER[i]
                    raw_temp = backend.read_temp(BOARD_NUM, probe_num)

                    history[probe_num].append(raw_temp)
                    avg_temp = sum(history[probe_num]) / len(history[probe_num])

                    current_temps[probe_num] = convert_temperature(avg_temp, probe_num)
                except Exception as e:
                    print(f"[TEMP] Runtime error: {e}")
                    temperatures["current_temps"] = [-1000] * NUM_PROBES

            temperatures["current_temps"] = current_temps
            time.sleep(1 / 14)

    except Exception as e:
        print(f"[TEMP] Error: {e}")
        temperatures["current_temps"] = [-1000] * NUM_PROBES

    finally:
        backend.close(BOARD_NUM)
        print("[TEMP] Temperature thread stopped.")