import math
import time
from collections import deque

BOARD_NUM = 0
OFFSETS = [0.598540, 0.261689, 0.0, 0.101573, 0.0]
NUM_PROBES = 4


def convert_temperature(measured_temp, probe_no):
    return 1.293 * measured_temp - 9.828 + OFFSETS[probe_no]


# =========================================================
# WINDOWS BACKEND (mcculw)
# =========================================================
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


# =========================================================
# LINUX BACKEND (uldaq)
# =========================================================
class LinuxULDAQBackend:
    def __init__(self):
        from uldaq import (
            get_daq_device_inventory,
            DaqDevice,
            InterfaceType,
            TInFlag
        )

        self.get_daq_device_inventory = get_daq_device_inventory
        self.DaqDevice = DaqDevice
        self.InterfaceType = InterfaceType
        self.TInFlag = TInFlag

        self.daq_device = None
        self.t_in_device = None

    def connect(self, board_num):
        devices = self.get_daq_device_inventory(self.InterfaceType.USB)
        if not devices:
            raise RuntimeError("No ULDAQ devices found")

        self.daq_device = self.DaqDevice(devices[0])
        self.daq_device.connect()

        self.t_in_device = self.daq_device.get_t_in_device()

        print("[TEMP] Linux ULDAQ connected")

    def read_temp(self, board_num, channel):
        # ULDAQ reads temperature directly per channel
        return self.t_in_device.t_in(channel, self.TInFlag.DEFAULT)

    def close(self, board_num):
        if self.daq_device:
            self.daq_device.disconnect()
            self.daq_device.release()
            
            
import math
import time

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
        pass

    try:
        print('running linux DAQ')
        return LinuxULDAQBackend()
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
                raw_temp = backend.read_temp(BOARD_NUM, i)

                history[i].append(raw_temp)
                avg_temp = sum(history[i]) / len(history[i])

                current_temps[i] = convert_temperature(avg_temp, i)

            temperatures["current_temps"] = current_temps
            time.sleep(1 / 14)

    except Exception as e:
        print(f"[TEMP] Error: {e}")
        temperatures["current_temps"] = [-1000] * NUM_PROBES

    finally:
        backend.close(BOARD_NUM)
        print("[TEMP] Temperature thread stopped.")