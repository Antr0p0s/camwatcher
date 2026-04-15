import math
import time
import serial

PORT = "COM9"
BAUD = 9600
BYTESIZE = 7
PARITY = 'E'
STOPBITS = 1
TIMEOUT = 1

def get_vacuum_pressure(ser, channel="1"):
    """
    Standard Pfeiffer Handshake:
    1. Send 'PR1\r\n'
    2. Receive ACK (\x06)
    3. Send ENQ (\x05)
    4. Receive Data String (e.g., '0,1.013E+03')
    """
    try:
        # 1. Clear buffers to ensure fresh data
        ser.reset_input_buffer()

        # 2. Request Pressure for Channel 1
        ser.write(f"PR{channel}\r\n".encode())
        time.sleep(0.1)

        # 3. Read the response to the request
        resp = ser.read(ser.in_waiting)
        
        # If we get a NAK (\x15), the controller is unhappy
        if b'\x15' in resp:
            return None, "NAK (Rejected)"

        # 4. Trigger the data transfer with ENQ (ASCII 5)
        ser.write(b"\x05")
        time.sleep(0.1)

        # 5. Read the final string
        data_string = ser.read(ser.in_waiting).decode(errors='ignore').strip()
        
        # Pfeiffer format is usually: Status,Value (e.g. '0,6.800E+02')
        if "," in data_string:
            status, value = data_string.split(",")
            return value, status
        
        return data_string, "Unknown"

    except Exception as e:
        return None, f"Error: {e}"

def pressure_acquisition_thread(USE_FAKE_PRESSURE, pressure, stop_event):
    print("[PRESSURE] Pressure thread starting.")
    
    if not USE_FAKE_PRESSURE: # not faking the temperatures
        print(f"[PRESSURE] Opening {PORT} for Pfeiffer Vacuum Data...")
        try:
            ser = serial.Serial(
                port=PORT, 
                baudrate=BAUD, 
                bytesize=BYTESIZE, 
                parity=PARITY, 
                stopbits=STOPBITS, 
                timeout=TIMEOUT
            )

            while not stop_event.is_set():
                pressure_val = None
                pressure_val, status_code = get_vacuum_pressure(ser, "1")

                # update the UI variable
                if pressure_val:
                    pressure['current_pressure'] = float(pressure_val)
                    pressure['current_status'] = status_code
                else:
                    pressure['current_pressure'] = 1e5
                    pressure['current_status'] = status_code
                # Schedule next update in 1/14th of a second (fps = 7 so should be fine)
                # get_vacuum_pressure also has a build in delay so it might not be as accurate but whatever
                time.sleep(1/14) 

        except serial.SerialException as e:
            print(f"[PRESSURE] Could not open serial port: {e}")
            return pressure_acquisition_thread(True, pressure, stop_event)
        except KeyboardInterrupt:
            print("\n[PRESSURE] Monitoring stopped by user.")
        finally:
            if 'ser' in locals() and ser.is_open:
                ser.close()
                print("[PRESSURE] Serial port closed.")
    else: # fake data bitch
        start_time = time.time()
        print('[PRESSURE] Fake pressure loop started')
        pressure['current_status'] = 404
        while not stop_event.is_set():
            try:
                # Thread-safe update to the shared dictionary
                pressure['current_pressure'] = 10 + 4 * math.sin(math.pi * (time.time()-start_time)/10)

                time.sleep(1/14) #average fps is 7 so if we take temperatures double that frequency it should be fine 
            
            except Exception as e:
                print(f"[PRESSURE] Error: {e}")
                time.sleep(0.5)

    print("[PRESSURE] Pressure thread stopped.")