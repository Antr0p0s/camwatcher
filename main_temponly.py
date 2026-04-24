import threading
import time
import math
from collections import deque
import tkinter as tk
from mcculw import ul
from mcculw.enums import InterfaceType, TempScale
from mcculw.ul import ULError
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sys

# ---------------------------
# Config
# ---------------------------
USE_FAKE_TEMPS = False
PROBE_PORTS = [0, 1, 2, 3]
NUM_PROBES = len(PROBE_PORTS)

# ---------------------------
# Globals
# ---------------------------
recording = False
running = True

temps_buffer = []
timestamps_buffer = []

# ---------------------------
# Temp conversion
# ---------------------------
OFFSETS = [0.598540, 0.261689, 0.0, 0.101573, 0.0]

def convert_temperature(measured_temp, probe_no):
    return 1.293 * measured_temp - 9.828 + OFFSETS[probe_no]

# ---------------------------
# UI App
# ---------------------------
class TempMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Temp Recorder")
        self.root.geometry("550x800")
        self.root.configure(bg="#2c3e50")
        
        self.active_probe = 0

        self.start_time = time.time()
        self.history = [deque(maxlen=5) for _ in range(NUM_PROBES)]
        self.raw_history = [deque(maxlen=5) for _ in range(NUM_PROBES)]

        self.current_temps = [0.0] * NUM_PROBES
        self.raw_temps = [0.0] * NUM_PROBES
        self.lock = threading.Lock()

        # 🔥 Calibration state (per probe)
        self.expected_temp = [15.0] * NUM_PROBES
        self.calibration_data = [[] for _ in range(NUM_PROBES)]

        self.device_connected = False
        self.board_num = 0
        self.after_id = None

        self.setup_ui()

        if not USE_FAKE_TEMPS:
            self.init_daq()

        threading.Thread(target=self.temp_loop, daemon=True).start()
        threading.Thread(target=self.ui_loop, daemon=True).start()

    def init_daq(self):
        try:
            devices = ul.get_daq_device_inventory(InterfaceType.ETHERNET)
            if not devices:
                self.status.config(text="No DAQ Found", fg="#e74c3c")
                return

            ul.create_daq_device(self.board_num, devices[0])
            self.device_connected = True
            self.status.config(text=f"Connected: {devices[0].product_name}", fg="#2ecc71")
        except ULError as e:
            print(f"DAQ Error: {e.message}")
            self.status.config(text="DAQ Error", fg="#e74c3c")

    def setup_ui(self):
        tk.Label(self.root, text="Thermal Recorder",
                 font=("Arial", 18, "bold"),
                 bg="#2c3e50", fg="#ecf0f1").pack(pady=10)

        self.copy_btn = tk.Button(self.root, text="📋 Copy Current Temps",
                                 command=self.copy_to_clipboard,
                                 bg="#34495e", fg="#ecf0f1")
        self.copy_btn.pack(pady=5)

        # Probe rows
        colors = ["#3399ff", "#000000", "#ff4d4d", "#ffffff", "#3cff01"]
        self.temp_vars = []

        for i in range(NUM_PROBES):
            frame = tk.Frame(self.root, bg="#34495e")
            frame.pack(pady=5, padx=30, fill="x")

            tk.Label(frame, text=f"Probe {i+1}",
                     bg="#34495e", fg="#bdc3c7").pack(side="left")

            var = tk.StringVar(value="--.- °C")
            self.temp_vars.append(var)

            # Button (RIGHTMOST)
            btn = tk.Button(frame, text="📋 Sample",
                            bg="#34495e", fg="#ecf0f1")
            btn.config(command=lambda idx=i, b=btn: self.sample_point(idx, b))
            btn.pack(side="right", padx=(5, 0))

            # Temp display
            tk.Label(frame, textvariable=var,
                     font=("Courier", 16, "bold"),
                     bg="#34495e", fg=colors[i]).pack(side="right", padx=(0, 10))

        # Status
        self.status = tk.Label(self.root, text="Idle", bg="#2c3e50", fg="#95a5a6")
        self.status.pack(pady=10)

        # -------- Calibration Plot --------
        self.cal_fig, self.cal_ax = plt.subplots(figsize=(5, 3))
        self.cal_canvas = FigureCanvasTkAgg(self.cal_fig, master=self.root)
        self.cal_canvas.get_tk_widget().pack(pady=10)

        self.cal_lines = []
        for i in range(NUM_PROBES):
            line, = self.cal_ax.plot([], [], 'o-', label=f"P{i+1}")
            self.cal_lines.append(line)

        self.cal_ax.set_xlabel("Expected (°C)")
        self.cal_ax.set_ylabel("Measured (°C)")
        self.cal_ax.legend(fontsize='x-small', ncol=NUM_PROBES)
        self.cal_ax.grid(True, alpha=0.3)
        
        tk.Button(self.root, text="📋 Copy Dataset",
          command=self.copy_full_dataset,
          bg="#8e44ad", fg="white").pack(pady=5)

        # Reset button
        tk.Button(self.root, text="Reset Calibration",
                  command=self.reset_calibration,
                  bg="#e74c3c", fg="white").pack(pady=5)

    # ---------------------------
    # Sampling logic
    # ---------------------------
    def sample_point(self, index, button=None):
        with self.lock:
            measured = self.current_temps[index]
            raw = self.raw_temps[index]

        # 👉 set active probe
        self.active_probe = index

        expected = self.expected_temp[index]

        # Store: (expected, measured, raw)
        self.calibration_data[index].append((expected, measured, raw))

        # Step expected
        self.expected_temp[index] -= 0.5

        # Clipboard (single point)
        self.root.clipboard_clear()
        self.root.clipboard_append(f"{expected:.2f}\t{measured:.2f}\t{raw:.2f}")

        self.update_calibration_plot()

        if button:
            old = button.cget("text")
            button.config(text="✓", fg="#2ecc71")
            self.root.after(200, lambda: button.config(text=old, fg="#ecf0f1"))

        print(f"[CAL] Probe {index+1}: expected={expected:.2f}, measured={measured:.2f}, raw={raw:.2f}")

    def update_calibration_plot(self):
        idx = self.active_probe
        self.cal_ax.clear()

        self.cal_ax.set_title(f"Probe {idx+1} Calibration, expected: {self.expected_temp[idx]}")
        self.cal_ax.set_xlabel("Expected (°C)")
        self.cal_ax.set_ylabel("Temperature (°C)")
        self.cal_ax.grid(True, alpha=0.3)

        if self.calibration_data[idx]:
            data = np.array(self.calibration_data[idx])

            x = data[:, 0]  # expected
            measured = data[:, 1]
            raw = data[:, 2]

            self.cal_ax.plot(x, measured, 'o-', label="Measured")
            self.cal_ax.plot(x, raw, 's--', label="Raw")

        self.cal_ax.legend()
        self.cal_ax.invert_xaxis()
        self.cal_canvas.draw_idle()

    def reset_calibration(self):
        self.expected_temp = [15.0] * NUM_PROBES
        self.calibration_data = [[] for _ in range(NUM_PROBES)]
        self.update_calibration_plot()
        print("[CAL] Reset")

    # ---------------------------
    # Existing logic
    # ---------------------------
    def copy_to_clipboard(self):
        with self.lock:
            temp_strings = [f"{t:.2f}" for t in self.current_temps]
        self.root.clipboard_clear()
        self.root.clipboard_append("\t".join(temp_strings))

    def temp_loop(self):
        global running
        while running:
            t = time.time() - self.start_time
            temps_now, raw_now = [], []

            for i in range(NUM_PROBES):
                raw = 20 + 2 * math.sin(t / 5 + i)
                temp = convert_temperature(raw, i)

                self.history[i].append(temp)
                self.raw_history[i].append(raw)

                temps_now.append(sum(self.history[i]) / len(self.history[i]))
                raw_now.append(sum(self.raw_history[i]) / len(self.raw_history[i]))

            with self.lock:
                self.current_temps = temps_now
                self.raw_temps = raw_now

            time.sleep(0.05)

    def ui_loop(self):
        while running:
            with self.lock:
                temps = list(self.current_temps)
                raw = list(self.raw_temps)

            for i in range(NUM_PROBES):
                self.temp_vars[i].set(f"{temps[i]:.1f} ({raw[i]:.1f}) °C")

            time.sleep(0.2)

    def on_close(self):
        global running
        running = False
        self.root.destroy()
        sys.exit(0)
        
    def copy_full_dataset(self):
        idx = self.active_probe
        data = self.calibration_data[idx]

        if not data:
            return

        lines = ["Measured\tRaw"]
        for _, m, r in data:
            lines.append(f"{m:.2f}\t{r:.2f}")

        text = "\n".join(lines)

        self.root.clipboard_clear()
        self.root.clipboard_append(text)

        print(f"[CAL] Copied dataset for Probe {idx+1}")

# ---------------------------
# Run
# ---------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = TempMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()