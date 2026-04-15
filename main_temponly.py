import threading
import time
import math
import os
import sys
from collections import deque
from datetime import datetime

import numpy as np
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# =========================================================
# IMPORT YOUR BACKEND SYSTEM
# =========================================================
from resources.tempWorker import (
    get_backend,
    BOARD_NUM,
    NUM_PROBES,
    convert_temperature
)

# =========================================================
# CONFIG
# =========================================================
USE_FAKE_TEMPS = False
PROBE_PORTS = [0, 1, 2, 3]

# =========================================================
# GLOBAL STATE
# =========================================================
recording = False
running = True

temps_buffer = []
timestamps_buffer = []

OFFSETS = [0.598540, 0.261689, 0.0, 0.101573, 0.0]

# =========================================================
# UI APP
# =========================================================
class TempMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Temp Recorder (Backend Version)")
        self.root.geometry("520x650")
        self.root.configure(bg="#2c3e50")

        self.start_time = time.time()

        self.history = [deque(maxlen=5) for _ in range(NUM_PROBES)]
        self.current_temps = [0.0] * NUM_PROBES
        self.lock = threading.Lock()

        self.after_id = None

        # =====================================================
        # BACKEND (REPLACES ALL MCCULW LOGIC)
        # =====================================================
        self.backend = get_backend(USE_FAKE_TEMPS)
        self.backend.connect()

        # =====================================================
        # UI
        # =====================================================
        self.setup_ui()

        # Threads
        self.worker_thread = threading.Thread(target=self.temp_loop, daemon=True)
        self.worker_thread.start()

        self.ui_thread = threading.Thread(target=self.ui_loop, daemon=True)
        self.ui_thread.start()

    # =========================================================
    # UI SETUP
    # =========================================================
    def setup_ui(self):
        tk.Label(
            self.root,
            text="Thermal Recorder (Unified Backend)",
            font=("Arial", 16, "bold"),
            bg="#2c3e50",
            fg="#ecf0f1"
        ).pack(pady=10)

        self.copy_btn = tk.Button(
            self.root,
            text="📋 Copy Current Temps",
            command=self.copy_to_clipboard,
            bg="#34495e",
            fg="#ecf0f1"
        )
        self.copy_btn.pack(pady=5)

        name_frame = tk.Frame(self.root, bg="#2c3e50")
        name_frame.pack(pady=5)

        tk.Label(
            name_frame,
            text="Filename:",
            bg="#2c3e50",
            fg="#bdc3c7"
        ).pack(side="left")

        self.filename_entry = tk.Entry(name_frame, width=25)
        self.filename_entry.insert(0, "experiment_1")
        self.filename_entry.pack(side="left", padx=5)

        colors = ["#3399ff", "#000000", "#ff4d4d", "#ffffff", "#3cff01"]
        self.temp_vars = []

        for i in range(NUM_PROBES):
            frame = tk.Frame(self.root, bg="#34495e")
            frame.pack(pady=5, padx=30, fill="x")

            tk.Label(
                frame,
                text=f"Probe {i+1}",
                bg="#34495e",
                fg="#bdc3c7"
            ).pack(side="left")

            var = tk.StringVar(value="--.- °C")
            self.temp_vars.append(var)

            tk.Label(
                frame,
                textvariable=var,
                font=("Courier", 16, "bold"),
                bg="#34495e",
                fg=colors[i % len(colors)]
            ).pack(side="right")

        self.status = tk.Label(self.root, text="Idle", bg="#2c3e50", fg="#95a5a6")
        self.status.pack(pady=10)

        self.btn = tk.Button(
            self.root,
            text="Start Recording",
            command=self.toggle_recording,
            bg="#e1e1e1"
        )
        self.btn.pack(pady=10)

        # Graph
        self.fig, self.ax = plt.subplots(figsize=(5, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(pady=10)

        self.lines = []
        for i in range(NUM_PROBES):
            line, = self.ax.plot([], [], label=f"P{i+1}")
            self.lines.append(line)

        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Temp (°C)")
        self.ax.legend(fontsize='x-small')
        self.ax.grid(True, alpha=0.3)

        self.update_graph()

    # =========================================================
    # COPY TO CLIPBOARD
    # =========================================================
    def copy_to_clipboard(self):
        with self.lock:
            temp_strings = [f"{t:.2f}" for t in self.current_temps]

        self.root.clipboard_clear()
        self.root.clipboard_append("\t".join(temp_strings))

        old = self.copy_btn.cget("text")
        self.copy_btn.config(text="✓ Copied!")
        self.root.after(1500, lambda: self.copy_btn.config(text=old))

    # =========================================================
    # GRAPH UPDATE
    # =========================================================
    def update_graph(self):
        if not running:
            return

        if len(timestamps_buffer) > 1:
            try:
                t = np.array(timestamps_buffer)
                y = np.array(temps_buffer)

                for i, line in enumerate(self.lines):
                    line.set_data(t, y[:, i])

                self.ax.relim()
                self.ax.autoscale_view()
                self.canvas.draw_idle()

            except Exception:
                pass

        self.after_id = self.root.after(500, self.update_graph)

    # =========================================================
    # RECORDING
    # =========================================================
    def toggle_recording(self):
        global recording
        recording = not recording

        if recording:
            self.btn.config(text="Pause Recording")
            self.status.config(text="Recording...", fg="#2ecc71")
        else:
            self.btn.config(text="Resume Recording")
            self.status.config(text="Paused", fg="#f39c12")

    # =========================================================
    # TEMP LOOP (BACKEND-BASED)
    # =========================================================
    def temp_loop(self):
        global running

        while running:
            current_time = time.time() - self.start_time
            temps_now = []

            for i in range(NUM_PROBES):
                try:
                    raw = self.backend.read_temp(BOARD_NUM, PROBE_PORTS[i])
                except Exception:
                    raw = 0.0

                temp = convert_temperature(raw, i)

                self.history[i].append(temp)
                avg = sum(self.history[i]) / len(self.history[i])

                temps_now.append(avg)

            with self.lock:
                self.current_temps = temps_now

            if recording:
                timestamps_buffer.append(current_time)
                temps_buffer.append(temps_now)

            time.sleep(0.5)

    # =========================================================
    # UI LOOP
    # =========================================================
    def ui_loop(self):
        while running:
            with self.lock:
                temps = list(self.current_temps)

            for i in range(NUM_PROBES):
                self.temp_vars[i].set(f"{temps[i]:.1f} °C")

            time.sleep(0.2)

    # =========================================================
    # SAVE
    # =========================================================
    def save_results(self):
        if not timestamps_buffer:
            return

        os.makedirs("output", exist_ok=True)

        name = self.filename_entry.get().strip() or datetime.now().strftime("%Y%m%d_%H%M%S")

        np.savez(
            f"output/{name}.npz",
            timestamps=np.array(timestamps_buffer),
            temperatures=np.array(temps_buffer)
        )

        plt.figure()
        arr = np.array(temps_buffer)

        for i in range(arr.shape[1]):
            plt.plot(timestamps_buffer, arr[:, i], label=f"P{i+1}")

        plt.legend()
        plt.grid()
        plt.savefig(f"output/{name}.png")
        plt.close()

    # =========================================================
    # CLOSE
    # =========================================================
    def on_close(self):
        global running, recording

        running = False
        recording = False

        if self.after_id:
            self.root.after_cancel(self.after_id)

        self.save_results()

        if hasattr(self, "backend"):
            self.backend.close(BOARD_NUM)

        self.root.destroy()
        sys.exit(0)


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = TempMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()