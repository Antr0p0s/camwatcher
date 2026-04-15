#!/usr/bin/env python3
"""
E-TC connection test — works through each stage so you can see exactly where it fails.
"""
import sys

DAQ_IP      = "192.168.0.101"  # factory default; try .100 if this fails
CONNECT_CODE = 0               # default, change if you set one on the device

# ── STEP 1: construct device object and open socket ───────────────────────────
print(f"\n[1] Opening connection to {DAQ_IP}...")
try:
    from resources.MCCDAQ.mccEthernet import mccEthernetDevice, ETC_PID
except ImportError:
    ETC_PID = 0x0138
    from resources.MCCDAQ.mccEthernet import mccEthernetDevice

try:
    device = mccEthernetDevice(ETC_PID, DAQ_IP)
    device.mccOpenDevice(CONNECT_CODE)
    device.printDeviceInfo()
    print(f"    OK - TCP socket open: {device.sock.getpeername()}")
except Exception as e:
    print(f"    FAIL: {e}")
    print("\n    Checklist:")
    print("      - Is the device powered and connected?")
    print("      - Try IP 192.168.0.101 (factory default) if using .100")
    print("      - Are you on the same subnet (192.168.0.x)?")
    print("      - Try: ping", DAQ_IP)
    sys.exit(1)

# ── STEP 2: construct E_TC (immediately reads MAC via ConfigMemory_R) ─────────
print("\n[2] Constructing E_TC (reads MAC address from device)...")
try:
    from resources.MCCDAQ.E_TC import E_TC
    dev = E_TC(device)
    print(f"    OK - MAC: {dev.device.MAC:012X}")
except Exception as e:
    print(f"    FAIL: {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

# ── STEP 3: Status ────────────────────────────────────────────────────────────
print("\n[3] Reading device status...")
try:
    status = dev.Status()
    print(f"    OK - status = {hex(status)}")
except Exception as e:
    print(f"    FAIL: {e}")

# ── STEP 4: Blink LED — visual confirmation the right device responded ────────
print("\n[4] Blinking LED 3x (watch the device)...")
try:
    dev.Blink(3)
    print("    OK")
except Exception as e:
    print(f"    FAIL: {e}")

# ── STEP 5: Read TC channel config ────────────────────────────────────────────
print("\n[5] Reading thermocouple channel configuration...")
try:
    dev.TinConfig_R()
    tc_names = {0:"disabled", 1:"J", 2:"K", 3:"T", 4:"E", 5:"R", 6:"S", 7:"B", 8:"N"}
    for i, v in enumerate(dev.config_values):
        print(f"    Ch{i}: {tc_names.get(v, f'unknown({v})')}")
except Exception as e:
    print(f"    FAIL: {e}")

# ── STEP 6: Read temperatures ─────────────────────────────────────────────────
print("\n[6] Reading temperatures (channels 0-3, mask=0x0F)...")
try:
    # Tin(channel_mask, units=0 Celsius, wait=0 return current value)
    temps = dev.Tin(0x0F, 0, 0)
    special = {-6666.0: "OVER RANGE", -8888.0: "OPEN TC", -9999.0: "DISABLED"}
    for i, t in enumerate(temps):
        print(f"    Ch{i}: {special.get(t, f'{t:.2f} °C')}")
except Exception as e:
    print(f"    FAIL: {e}")

# ── CLEANUP ───────────────────────────────────────────────────────────────────
try:
    device.sock.close()
except Exception:
    pass

print("\n[DONE]")