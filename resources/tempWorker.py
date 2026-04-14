from mcculw import ul
from mcculw.enums import InterfaceType, TempScale
from mcculw.ul import ULError
from collections import deque
import math
import time

BOARD_NUM = 0
# offset of all the TC's - TC 3 is calibrated and is the reference temperature - TC5 is garbage
# standard deviation is 0.05 degree C or just make it 0.1 its fineeee
# without offset TC 3 is the highest so a positive offset for all probes makes sense
OFFSETS = [0.598540, 0.261689, 0.0, 0.101573, 0.0]
NUM_PROBES = 4

def convert_temperature(measured_temp, probe_no):
    return 1.293 * measured_temp - 9.828 + OFFSETS[probe_no]

def temperature_acquisition_thread(USE_FAKE_TEMPS, temperatures, stop_event):
    print("[TEMP] Temperature thread started.")
    
    if not USE_FAKE_TEMPS: # not faking the temperatures
        devices = ul.get_daq_device_inventory(InterfaceType.ETHERNET)
        if not devices:
            print("No Ethernet DAQ devices found!")
            return
        
        device = devices[0]
        history = [deque(maxlen=5) for _ in range(NUM_PROBES)] # moving average over 4 intervals

        try:
            ul.create_daq_device(BOARD_NUM, device)
        except ULError:
            ul.release_daq_device(BOARD_NUM)
            ul.create_daq_device(BOARD_NUM, device)
        print(f"Connected to: {device.product_name} ({device.unique_id})")

        while not stop_event.is_set():
            try:
                current_temps = [0,0,0,0]
                for i in range(NUM_PROBES):
                    # 1. Read raw temperature
                    raw_temp = ul.t_in(BOARD_NUM, i, TempScale.CELSIUS)
                    
                    # 2. Add to history
                    history[i].append(raw_temp)
                    
                    # 3. Calculate Moving Average
                    avg_temp = sum(history[i]) / len(history[i])
                    
                    # 4. Update UI Variable
                    current_temps[i] = convert_temperature(avg_temp, i)

                # update the UI variable
                temperatures['current_temps'] = current_temps
                # Schedule next update in 1/14th of a second (fps = 7 so should be fine)
                time.sleep(1/14) 
        
            except ULError as e:
                print(f"[TEMP] UL Error: {e.message}")
                temperatures['current_temps'] = [-1000, -1000, -1000, -1000, -1000]
                time.sleep(0.5)
            except Exception as e:
                print(f"[TEMP] Error: {e}")
                temperatures['current_temps'] = [-1000, -1000, -1000, -1000, -1000]
                time.sleep(0.5)
    else:
        start_time = time.time()
        while not stop_event.is_set():
            try:
                current_temps = [0,0,0,0]
                for i in range(0, NUM_PROBES):
                    temp = 15 + 4 * math.sin(math.pi * ((i+1)/1.8) * (time.time()-start_time)/10)
                                
                    current_temps[i] = temp + i
            
                # Thread-safe update to the shared dictionary
                temperatures['current_temps'] = current_temps

                time.sleep(1/14) #average fps is 7 so if we take temperatures double that frequency it should be fine 
            
            except Exception as e:
                print(f"[TEMP] Error: {e}")
                time.sleep(0.5)

    ul.release_daq_device(BOARD_NUM)
    print("[TEMP] Temperature thread stopped.")