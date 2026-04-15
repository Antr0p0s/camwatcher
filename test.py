import time
from resources.MCCDAQ.E_TC import E_TC, mccEthernetDevice


# =========================
# CONFIG
# =========================
DAQ_IP = "192.168.0.101"   # <-- CHANGE THIS
CHANNELS = 4
BOARD_NUM = 0


def convert_temperature(raw):
    # keep simple for debugging (no calibration yet)
    return raw


def main():
    print("[INIT] Connecting to E-TC device...")

    # Build device manually (NO discovery)
    device = mccEthernetDevice()
    device.address = DAQ_IP

    try:
        dev = E_TC(device)
        dev.open()
    except Exception as e:
        print("[ERROR] Could not connect to device:", e)
        return

    print("[OK] Connected. Reading temperatures...\n")

    try:
        while True:
            temps = []

            for ch in range(CHANNELS):
                try:
                    raw = dev.t_in(ch)
                    temps.append(convert_temperature(raw))
                except Exception as e:
                    temps.append(float("nan"))
                    print(f"[WARN] Channel {ch} read failed:", e)

            print("Temps:", " | ".join(f"{t:6.2f}" for t in temps))
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[EXIT] Stopping...")

    finally:
        try:
            dev.close()
        except:
            pass


if __name__ == "__main__":
    main()