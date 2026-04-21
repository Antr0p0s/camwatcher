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
PROBE_PORTS = [0, 1, 2, 3, 7]
NUM_PROBES = len(PROBE_PORTS)

# ---------------------------
# Globals
# ---------------------------
recording = False
running = True

# Data storage for recording
temps_buffer = []
timestamps_buffer = []

# ---------------------------
# Temp conversion
# ---------------------------
OFFSETS = [0.598540, 0.261689, 0.0, 0.101573, 0.0]

def convert_temperature(measured_temp, probe_no):
    # return 1.293 * measured_temp - 9.828 + OFFSETS[2]
    return 1.293 * measured_temp - 9.828 + OFFSETS[probe_no]

# ---------------------------
# UI App
# ---------------------------
class TempMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Temp Recorder")
        self.root.geometry("500x650")
        self.root.configure(bg="#2c3e50")

        self.start_time = time.time()
        self.history = [deque(maxlen=5) for _ in range(NUM_PROBES)]

        self.current_temps = [0.0] * NUM_PROBES
        self.lock = threading.Lock()

        self.device_connected = False
        self.board_num = 0
        self.after_id = None

        self.setup_ui()

        if not USE_FAKE_TEMPS:
            self.init_daq()

        # Threads
        self.worker_thread = threading.Thread(target=self.temp_loop, daemon=True)
        self.worker_thread.start()

        self.ui_thread = threading.Thread(target=self.ui_loop, daemon=True)
        self.ui_thread.start()

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

        # Copy Button
        self.copy_btn = tk.Button(self.root, text="📋 Copy Current Temps", 
                                 command=self.copy_to_clipboard,
                                 bg="#34495e", fg="#ecf0f1",
                                 activebackground="#1abc9c")
        self.copy_btn.pack(pady=5)

        # Filename input
        name_frame = tk.Frame(self.root, bg="#2c3e50")
        name_frame.pack(pady=5)
        tk.Label(name_frame, text="Filename:", bg="#2c3e50", fg="#bdc3c7").pack(side="left")
        self.filename_entry = tk.Entry(name_frame, width=25)
        self.filename_entry.insert(0, "experiment_1")
        self.filename_entry.pack(side="left", padx=5)

        colors = ["#3399ff", "#000000", "#ff4d4d", "#ffffff", "#3cff01"]
        self.temp_vars = []

        for i in range(NUM_PROBES):
            frame = tk.Frame(self.root, bg="#34495e")
            frame.pack(pady=5, padx=30, fill="x")
            tk.Label(frame, text=f"Probe {i+1}", bg="#34495e", fg="#bdc3c7").pack(side="left")
            
            var = tk.StringVar(value="--.- °C")
            self.temp_vars.append(var)
            tk.Label(frame, textvariable=var, font=("Courier", 16, "bold"),
                     bg="#34495e", fg=colors[i]).pack(side="right")

        self.status = tk.Label(self.root, text="Idle", bg="#2c3e50", fg="#95a5a6")
        self.status.pack(pady=10)

        self.btn = tk.Button(self.root, text="Start Recording",
                             command=self.toggle_recording, bg="#e1e1e1")
        self.btn.pack(pady=10)

        # Live Graph
        self.fig, self.ax = plt.subplots(figsize=(5, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(pady=10)

        self.lines = []
        for i in range(NUM_PROBES):
            line, = self.ax.plot([], [], label=f"P{i+1}")
            self.lines.append(line)

        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Temp (°C)")
        self.ax.legend(fontsize='x-small', ncol=NUM_PROBES)
        self.ax.grid(True, alpha=0.3)
        self.update_graph()

    def copy_to_clipboard(self):
        with self.lock:
            temp_strings = [f"{t:.2f}" for t in self.current_temps]
        excel_data = "\t".join(temp_strings)
        self.root.clipboard_clear()
        self.root.clipboard_append(excel_data)
        
        old_text = self.copy_btn.cget("text")
        self.copy_btn.config(text="✓ Copied!", fg="#2ecc71")
        self.root.after(1500, lambda: self.copy_btn.config(text=old_text, fg="#ecf0f1"))

    def update_graph(self):
        if not running or not self.root.winfo_exists():
            return

        if len(timestamps_buffer) > 1:
            try:
                time_arr = np.array(timestamps_buffer)
                temps_arr = np.array(temps_buffer)
                for i, line in enumerate(self.lines):
                    line.set_data(time_arr, temps_arr[:, i])
                self.ax.relim()
                self.ax.autoscale_view()
                self.canvas.draw_idle()
            except Exception:
                pass

        self.after_id = self.root.after(500, self.update_graph)

    def toggle_recording(self):
        global recording
        recording = not recording
        if recording:
            self.btn.config(text="Pause Recording")
            self.status.config(text="Recording...", fg="#2ecc71")
        else:
            self.btn.config(text="Resume Recording")
            self.status.config(text="Paused", fg="#f39c12")

    def temp_loop(self):
        global running
        while running:
            current_time = time.time() - self.start_time
            temps_now = []

            # 1. ALWAYS Read Temperatures
            for i in range(NUM_PROBES):
                if USE_FAKE_TEMPS:
                    raw = 20 + 2 * math.sin(current_time / 5 + i)
                else:
                    try:
                        raw = ul.t_in(self.board_num, PROBE_PORTS[i], TempScale.CELSIUS)
                    except ULError:
                        raw = 0.0

                temp = convert_temperature(raw, i)
                self.history[i].append(temp)
                avg = sum(self.history[i]) / len(self.history[i])
                temps_now.append(avg)

            # 2. ALWAYS update current_temps (for UI and Clipboard)
            with self.lock:
                self.current_temps = temps_now

            # 3. ONLY save to buffer if recording
            if recording:
                timestamps_buffer.append(current_time)
                temps_buffer.append(temps_now)

            time.sleep(0.5)

    def ui_loop(self):
        while running:
            with self.lock:
                temps = list(self.current_temps)
            try:
                for i in range(NUM_PROBES):
                    self.temp_vars[i].set(f"{temps[i]:.1f} °C")
            except Exception:
                break
            time.sleep(0.2)

    def save_results(self):
        if not timestamps_buffer:
            return
        os.makedirs("output", exist_ok=True)
        base_name = self.filename_entry.get().strip() or datetime.now().strftime("%Y%m%d_%H%M%S")
        
        np.savez(f"output/{base_name}.npz", 
                 timestamps=np.array(timestamps_buffer), 
                 temperatures=np.array(temps_buffer))
        
        plt.figure(figsize=(10, 6))
        t_arr = np.array(temps_buffer)
        for i in range(t_arr.shape[1]):
            plt.plot(timestamps_buffer, t_arr[:, i], label=f"P{i+1}")
        plt.legend(); plt.grid(True); plt.savefig(f"output/{base_name}.png"); plt.close()

    def on_close(self):
        global running, recording
        running = False
        recording = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.save_results()
        if self.device_connected:
            ul.release_daq_device(self.board_num)
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = TempMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()