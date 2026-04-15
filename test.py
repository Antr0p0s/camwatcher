from resources.MCCDAQ.E_TC import E_TC, mccDiscover
import time

def main():
    print("[INIT] Discovering device...")

    devices = mccDiscover()

    if not devices:
        print("[ERROR] No devices found")
        return

    device = devices[0]

    print("[OK] Found device:", device.address)

    tc = E_TC(device)
    tc.open()

    try:
        while True:
            temps = [tc.t_in(i) for i in range(4)]
            print("Temps:", temps)
            time.sleep(0.5)

    except KeyboardInterrupt:
        pass

    finally:
        tc.close()


if __name__ == "__main__":
    main()