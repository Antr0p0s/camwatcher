#!/usr/bin/env python3
"""
MCC E-TC temperature logger using wjasper Linux_Drivers
Reads thermocouple channels 0-3 continuously.
"""

import time
import math
from resources.MCCDAQ.E_TC import E_TC   # adjust import path to match your layout

# =========================
# CONFIG
# =========================
DAQ_IP   = "192.168.0.100"  # <-- change to your device IP
CHANNELS = 4                 # channels 0-3
INTERVAL = 0.5               # seconds between reads

# Thermocouple type: J=1, K=2, T=3, E=4, R=5, S=6, B=7, N=8
TC_TYPE  = E_TC.TC_TYPE_K

def main():
    print(f"[INIT] Connecting to E-TC at {DAQ_IP} ...")

    try:
        dev = E_TC(DAQ_IP)
    except Exception as e:
        print("[ERROR] Could not instantiate E_TC:", e)
        return

    print("[OK] Device object created.\n")

    # Configure each channel: set thermocouple type
    # Channel config is written as a list of types, one per channel (8 total)
    tc_types = [TC_TYPE] * 8
    try:
        dev.TCConfigW(tc_types)
        print("[OK] Thermocouple type configured.")
    except Exception as e:
        print("[WARN] Could not write TC config:", e)

    print("Reading temperatures (Ctrl+C to stop)...\n")

    try:
        while True:
            temps = []
            # Tin() takes a channel BITMASK, not an index
            # 0x01=ch0, 0x02=ch1, 0x04=ch2, 0x08=ch3 ... 0xFF=all 8
            channel_mask = (1 << CHANNELS) - 1  # e.g. 0x0F for 4 channels
            try:
                result = dev.Tin(channel_mask)
                # result is a list of floats, one per set bit, in channel order
                temps = list(result)
            except Exception as e:
                print("[ERROR] Tin() read failed:", e)
                temps = [float("nan")] * CHANNELS

            readings = " | ".join(
                f"Ch{i}: {t:7.2f} °C" if not math.isnan(t) else f"Ch{i}:    OPEN"
                for i, t in enumerate(temps[:CHANNELS])
            )
            print(readings)
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("\n[EXIT] Stopped by user.")
    finally:
        try:
            dev.sock.close()
            print("[CLEANUP] Socket closed.")
        except Exception:
            pass

if __name__ == "__main__":
    main()