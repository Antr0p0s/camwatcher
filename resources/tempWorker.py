import math
import time
from collections import deque

BOARD_NUM = 0
OFFSETS = [13.704, -2.8299, 27.852, -13.837] # blue, black, red, white
FIRST_COEFFICIENTS = [0.1612, 0.1097, 0.2452, 0.0076]
SECOND_COEFFICIENTS = [-3.0011, -1.1087, -5.1248, 1.3971]

# first, second, offset
FITS = [[0.125509,	-1.891261,	5.205203], # blue
[0.067673,	0.219476,	-16.208077], # black
[0.226843,	-4.587383,	23.984397], # red
[0.009988,	1.299066,	-12.197174]] # white

PROBE_ORDER=[3, 2, 1, 0] 
# blue = 0 - black = 1 - red = 2 - white = 3
NUM_PROBES = 4
MOV_AVG_LENGTH = 4

# gewilde orde: black, white, blue, red (1, 3, 0, 2)
def convert_temperature(measured_temp, probe_no):
    return FITS[probe_no][0] * measured_temp * measured_temp + FITS[probe_no][1] * measured_temp + FITS[probe_no][2]
    # return FIRST_COEFFICIENTS[probe_no] * measured_temp * measured_temp + SECOND_COEFFICIENTS[probe_no] * measured_temp + OFFSETS[probe_no]

class MCCBackend:
    def __init__(self):
        from mcculw import ul
        from mcculw.enums import InterfaceType, TempScale, TcType
        from mcculw.ul import ULError

        self.ul = ul
        self.InterfaceType = InterfaceType
        self.TempScale = TempScale
        self.ULError = ULError
        self.TcType = TcType

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
        return MCCBackend()
    
    except NameError:
        raise RuntimeError(
            "No DAQ backend available"
        )


# =========================================================
# MAIN THREAD
# =========================================================
def temperature_acquisition_thread(USE_FAKE_TEMPS, temperatures, stop_event):
    print("[TEMP] Temperature thread started.")

    backend = get_backend(USE_FAKE_TEMPS)
    backend.connect(BOARD_NUM)

    history = [deque(maxlen=MOV_AVG_LENGTH) for _ in range(NUM_PROBES)]

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