import time
from pyfirmata2 import Arduino

# Configuration
PORT = 'COM12'  # Replace with your actual port
SUPPLY_VOLTS = 5.0

# 1. Define the callback function that handles new data
def on_analog_reading(value):
    # 'value' is already normalized between 0.0 and 1.0
    sensor_value = int(value * 1023)
    measured_voltage = value * SUPPLY_VOLTS
    print(f"Analog Value: {sensor_value} | Voltage: {measured_voltage:.2f} V")

# 2. Initialize Arduino board
board = Arduino(PORT)

# 3. Register the callback to the specific analog pin
# (a = analog, 0 = pin number, r = input/read)
analog_pin = board.get_pin('a:0:r')
analog_pin.register_callback(on_analog_reading)
analog_pin.enable_reporting()

# 4. Set the sampling interval in milliseconds (matching your 1000ms delay)
board.samplingOn(1000)

print("Starting reading loop... Press Ctrl+C to stop.")

# 5. Keep the main thread alive
try:
    while True:
        time.sleep(1)  # Just sleep; the callback handles the printing

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    board.exit()