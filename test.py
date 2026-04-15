#!/usr/bin/env python3
"""
E-TC connection test - run this to diagnose exactly where the failure is.
"""
import socket
import sys

DAQ_IP   = "192.168.0.100"   # factory default; change if yours differs
DAQ_PORT = 54211              # MCC Ethernet device port (UDP)

# ── STEP 1: basic network reachability ───────────────────────────────────────
print(f"\n[1] Pinging {DAQ_IP} via UDP probe...")
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2.0)
    s.connect((DAQ_IP, DAQ_PORT))
    print(f"    OK - socket can reach {DAQ_IP}:{DAQ_PORT}")
    s.close()
except OSError as e:
    print(f"    FAIL - network error: {e}")
    print("    Check: Is the device powered? Same subnet? Right IP?")
    sys.exit(1)

# ── STEP 2: construct mccEthernetDevice and open socket ──────────────────────
print("\n[2] Constructing mccEthernetDevice...")
try:
    from resources.MCCDAQ.mccEthernet import mccEthernetDevice, EthernetDeviceInfo
    device = mccEthernetDevice(0x0138, DAQ_IP)   # ETC_PID = 0x0138
    print(f"    OK - device object created")
    print(f"    sock type : {type(device.sock)}")
    print(f"    remote    : {device.sock.getpeername()}")
except Exception as e:
    print(f"    FAIL: {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

# ── STEP 3: construct E_TC (this immediately calls MACaddress → ConfigMemory_R)
print("\n[3] Constructing E_TC (reads MAC from device)...")
try:
    from resources.MCCDAQ.E_TC import E_TC
    dev = E_TC(device)
    print(f"    OK - E_TC constructed")
    mac = dev.device.MAC
    print(f"    MAC address: {mac:012X}")
except Exception as e:
    print(f"    FAIL: {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

# ── STEP 4: Status command ────────────────────────────────────────────────────
print("\n[4] Reading device status...")
try:
    status = dev.Status()
    print(f"    OK - status = {hex(status)}")
except Exception as e:
    print(f"    FAIL: {e}")

# ── STEP 5: Blink LED (visual confirmation) ───────────────────────────────────
print("\n[5] Blinking LED 3x (watch the device)...")
try:
    dev.Blink(3)
    print("    OK - blink command sent")
except Exception as e:
    print(f"    FAIL: {e}")

# ── STEP 6: Read TC config ────────────────────────────────────────────────────
print("\n[6] Reading thermocouple channel config...")
try:
    dev.TinConfig_R()
    tc_names = {0:"disabled",1:"J",2:"K",3:"T",4:"E",5:"R",6:"S",7:"B",8:"N"}
    for i, v in enumerate(dev.config_values):
        print(f"    Ch{i}: {tc_names.get(v, f'unknown({v})')}")
except Exception as e:
    print(f"    FAIL: {e}")

# ── STEP 7: Read temperatures ─────────────────────────────────────────────────
print("\n[7] Reading temperatures (channels 0-3, mask=0x0F)...")
try:
    # Tin(channel_mask, units, wait)
    # units: 0=Celsius, wait: 0=current value
    temps = dev.Tin(0x0F, 0, 0)
    special = {-6666.0: "OVER RANGE", -8888.0: "OPEN TC", -9999.0: "DISABLED"}
    for i, t in enumerate(temps):
        label = special.get(t, f"{t:.2f} °C")
        print(f"    Ch{i}: {label}")
except Exception as e:
    print(f"    FAIL: {e}")

# ── CLEANUP ───────────────────────────────────────────────────────────────────
try:
    device.sock.close()
except Exception:
    pass

print("\n[DONE]")