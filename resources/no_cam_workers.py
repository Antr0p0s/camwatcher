import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

SAVE_LOC = r'P:\PIN\Users\Jelmer\no video data'

def save_data(temperatures, pressures, timestamps):
    BASE_SAVE_LOC = (f"{SAVE_LOC}\\{datetime.now().strftime('%Y-%m-%d-%H-%M')}")
    # BASE_SAVE_LOC = (f"{SAVE_LOC}\\testing")
    os.makedirs(SAVE_LOC, exist_ok=True)
    os.makedirs(BASE_SAVE_LOC, exist_ok=True)

    # Convert to numpy arrays
    temps = np.array(temperatures)
    press = np.array(pressures)
    ts = np.array(timestamps)

    # ===== SAVE NUMPY DATA =====
    np.savez(
        os.path.join(BASE_SAVE_LOC, "temperatures.npz"),
        temperatures=temps,
        timestamps=ts
    )
    np.savez(
        os.path.join(BASE_SAVE_LOC, "pressures.npz"),
        pressures=pressures,
        timestamps=ts
    )

    # ===== PRESSURE PLOT =====
    fig_p, ax_p = plt.subplots(figsize=(10, 4), dpi=100)
    ax_p.plot(ts, press, color="#9400D3", linewidth=1.5)
    ax_p.set_title("Pressure Profile")
    ax_p.set_ylabel("Pressure (mbar)")
    ax_p.set_xlabel("Time (s)")
    ax_p.set_ylim(0, 20)
    ax_p.grid(True, alpha=0.3)

    pressure_path = os.path.join(BASE_SAVE_LOC, "pressure.png")
    fig_p.savefig(pressure_path)
    plt.close(fig_p)

    # ===== TEMPERATURE PLOT =====
    fig_t, ax_t = plt.subplots(figsize=(10, 4), dpi=100)

    colors = ["#ff4d4d", "#ff9933", "#33cc33", "#3399ff", "#b700ff"]

    if temps.ndim == 1:
        temps = temps[:, np.newaxis]

    num_probes = temps.shape[1]

    for j in range(min(5, num_probes)):
        ax_t.plot(ts, temps[:, j], color=colors[j], label=f"Probe {j+1}")

    ax_t.set_title("Temperature Profiles")
    ax_t.set_ylabel("Temp (°C)")
    ax_t.set_xlabel("Time (s)")
    ax_t.legend(loc="upper right", fontsize="x-small", ncol=3)
    ax_t.grid(True, alpha=0.3)

    temperature_path = os.path.join(BASE_SAVE_LOC, "temperature.png")
    fig_t.savefig(temperature_path)
    plt.close(fig_t)

    print(f"Data and plots saved to: {BASE_SAVE_LOC}")