import serial
import time

# --- Configuration (Adjust COM port as needed) ---
PORT = "COM9"
BAUD = 9600
BYTESIZE = 7
PARITY = 'E'
STOPBITS = 1
TIMEOUT = 1

def fix_over_range(ser):
    print("Attempting to clear 'OR' status...")
    
    # 1. Gain Priority
    ser.write(b"FRI,1\r\n")
    time.sleep(0.1)
    
    # 2. Send Atmosphere Set (ATS)
    # This forces the 'OR' voltage to become '1000 mbar'
    print("Sending ATS,1 command...")
    ser.write(b"ATS,1\r\n")
    time.sleep(0.5)
    
    ack = ser.read(ser.in_waiting)
    if b'\x06' in ack:
        print("--> Success! The 'OR' should clear on the display.")
    else:
        print(f"--> Failed: {ack}. The signal may be too far out of range to calibrate.")
        
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

        print("Connection Successful. Calibrating..")
        fix_over_range(ser)

    except serial.SerialException as e:
        print(f"Could not open serial port: {e}")
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial port closed.")