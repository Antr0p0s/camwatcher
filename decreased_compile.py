import os
import numpy as np
import matplotlib.pyplot as plt
from resources.decreased.compiler import compile_video
import asyncio
import shutil
import time
import gc

def delete_folder(path, retries=5, delay=0.5):
    path = os.path.abspath(path)
    gc.collect()
    time.sleep(0.5)

    for i in range(retries):
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
            print(f"[CLEANUP] Deleted: {path}")
            return
        except PermissionError as e:
            print(f"[CLEANUP] Locked, retry {i+1}/{retries}")
            time.sleep(delay)

    print(f"[CLEANUP] FAILED to delete: {path} (still locked)")

def compile_data(input_folder):
    base_path = f'./data/chunks/{input_folder}'
    files = [f for f in os.listdir(base_path) if f.endswith(".npz")]

    if not files:
        print("No files found.")
        return

    # 🔥 Sort by chunk index (chunk_0.npz, chunk_1.npz, ...)
    files.sort(key=lambda x: int(x.split("_")[1].split(".")[0]))

    all_timestamps = []
    all_temps = []
    all_pressures = []
    all_frames = []

    print(f"[INFO] Found {len(files)} chunk files")

    for f in files:
        path = os.path.join(base_path, f)

        try:
            with np.load(path) as data:
                timestamps = data["timestamps"]
                temps = data["temperatures"]
                pressures = data["pressures"]
                frames = data["frames"]

                all_timestamps.append(timestamps)
                all_temps.append(temps)
                all_pressures.append(pressures)
                all_frames.append(frames)

        except Exception as e:
            print(f"[WARN] Skipping {f}: {e}")

    # 🔥 Concatenate everything
    frames = np.concatenate(all_frames)
    timestamps = np.concatenate(all_timestamps)
    temps = np.concatenate(all_temps)
    pressures = np.concatenate(all_pressures)

    print(f"[INFO] Total samples: {len(timestamps)}")

    # ---------------------------
    # Save combined datasets
    # ---------------------------
    os.makedirs("./data/compiled", exist_ok=True)
    os.makedirs(f"./data/compiled/{input_folder}", exist_ok=True)

    np.savez(
        f"./data/compiled/{input_folder}/temperature.npz",
        timestamps=timestamps,
        temperatures=temps
    )

    np.savez(
        f"./data/compiled/{input_folder}/pressure.npz",
        timestamps=timestamps,
        pressures=pressures
    )

    print("[INFO] Saved compiled NPZ files")

    # ---------------------------
    # Plot TEMPERATURE
    # ---------------------------
    plt.figure()

    if temps.ndim == 2:
        for i in range(temps.shape[1]):
            plt.plot(timestamps, temps[:, i], label=f"T{i+1}")
        plt.legend()
    else:
        plt.plot(timestamps, temps)

    plt.xlabel("Time (s)")
    plt.ylabel("Temperature")
    plt.title("Temperature vs Time")
    plt.grid()

    temp_plot_path = f"./data/compiled/{input_folder}/temperature.png"
    plt.savefig(temp_plot_path)
    plt.close()

    # ---------------------------
    # Plot PRESSURE
    # ---------------------------
    plt.figure()

    if pressures.ndim == 2:
        for i in range(pressures.shape[1]):
            plt.plot(timestamps, pressures[:, i], label=f"P{i+1}")
        plt.legend()
    else:
        plt.plot(timestamps, pressures)

    plt.xlabel("Time (s)")
    plt.ylabel("Pressure")
    plt.title("Pressure vs Time")
    plt.grid()

    pressure_plot_path = f"./data/compiled/{input_folder}/pressure.png"
    plt.savefig(pressure_plot_path)
    plt.close()

    print("[INFO] Saved plots:")
    print(" -", temp_plot_path)
    print(" -", pressure_plot_path)

    data = {
        "frames": frames,
        "timestamps": timestamps,
        "temperatures": temps,
        "pressures": pressures
    }
    output_path = f"./data/compiled/{input_folder}/video.mp4"

    asyncio.run(compile_video(data, output_path))

    delete_folder(base_path)

def main_menu():
    measurements = os.listdir('./data/chunks')
    
    if not measurements:
        print("No measurements found.")
        return

    print("\n=== AVAILABLE MEASUREMENTS (Newest at Bottom) ===")
    for i, b in enumerate(measurements):
        print(f"[{i}] {b}")

    print(f"[x] Cancel")

    try:
        user_input = input("\nSelect a backup number to compile: ")
        if user_input.lower() == 'q' or user_input.lower() == 'x':
            print("Operation cancelled.")
            return
        
        choice = int(user_input)
        compile_data(measurements[choice])

    except (ValueError, IndexError) as e:
        print(e)
        print("Invalid selection.")

if __name__ == "__main__":
    # compile_data('devtime')
    # delete_folder('./data/chunks/devtime')
    main_menu()

