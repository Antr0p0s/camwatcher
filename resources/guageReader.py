import serial
import time

# --- Configuration (Adjust COM port as needed) ---
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

# --- Main Loop ---
if __name__ == "__main__":
    print(f"Opening {PORT} for Pfeiffer Vacuum Data...")
    try:
        ser = serial.Serial(
            port=PORT, 
            baudrate=BAUD, 
            bytesize=BYTESIZE, 
            parity=PARITY, 
            stopbits=STOPBITS, 
            timeout=TIMEOUT
        )

        print("Connection Successful. Reading Pressure...")
        print("-" * 40)

        while True:
            pressure_val, status_code = get_vacuum_pressure(ser, "1")
            
            if pressure_val:
                # status_code '0' means measurement is valid
                print(f"[{time.strftime('%H:%M:%S')}] Pressure: {pressure_val} mbar | Status: {status_code}")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Reading Failed: {status_code}")

            time.sleep(1/14) # Frequency of updates

    except serial.SerialException as e:
        print(f"Could not open serial port: {e}")
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial port closed.")