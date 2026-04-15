import time
from resources.MCCDAQ.E_TC import E_TC, mccEthernetDevice, ETC_PID

# =========================
# CONFIG
# =========================
DAQ_IP = "192.168.0.100"   # <-- CHANGE THIS
CHANNELS = 4

def main():
    print("[INIT] Connecting to E-TC device...")

    # Build device with product ID and IP address
    device = mccEthernetDevice(ETC_PID, DAQ_IP)
    
    try:
        # Open the socket connection first
        device.mccOpenDevice()
        
        # Then initialize the E_TC class
        dev = E_TC(device)
    except Exception as e:
        print("[ERROR] Could not connect to device:", e)
        return

    print("[OK] Connected. Reading temperatures...\n")

    try:
        while True:
            temps = []

            for ch in range(CHANNELS):
                try:
                    raw = dev.Tin(ch)  # method might be Tin, not t_in
                    temps.append(raw)
                except Exception as e:
                    temps.append(float("nan"))
                    print(f"[WARN] Channel {ch} read failed:", e)

            print("Temps:", " | ".join(f"{t:6.2f}" for t in temps))
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[EXIT] Stopping...")

    finally:
        try:
            device.sock.close()
        except:
            pass


if __name__ == "__main__":
    main()
