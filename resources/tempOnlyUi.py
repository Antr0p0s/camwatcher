import time
import math
from collections import deque
import tkinter as tk

from workers import save_buffer_worker
from apiHandling import trigger_server_compilation

class TempMonitorApp:
    def __init__(self, root, num_probes):
        self.num_probes = num_probes
        self.root = root
        self.root.title("Temp Recorder")
        self.root.geometry("400x500")
        self.root.configure(bg="#2c3e50")

        self.start_time = time.time()
        self.history = [deque(maxlen=5) for _ in range(self.num_probes)]

        self.temp_vars = []
        self.setup_ui()

        self.update_loop()

    def setup_ui(self):
        tk.Label(self.root, text="Thermal Recorder",
                 font=("Arial", 18, "bold"),
                 bg="#2c3e50", fg="#ecf0f1").pack(pady=20)

        colors = ["#3399ff", "#000000", "#ff4d4d", "#ffffff", "#3cff01"]

        for i in range(self.num_probes):
            frame = tk.Frame(self.root, bg="#34495e")
            frame.pack(pady=8, padx=30, fill="x")

            tk.Label(frame, text=f"Probe {i+1}",
                     bg="#34495e", fg="#bdc3c7").pack(side="left")

            var = tk.StringVar(value="--.- °C")
            self.temp_vars.append(var)

            tk.Label(frame, textvariable=var,
                     font=("Courier", 18, "bold"),
                     bg="#34495e", fg=colors[i]).pack(side="right")

        self.status = tk.Label(self.root, text="Idle",
                               bg="#2c3e50", fg="#95a5a6")
        self.status.pack(pady=10)

        self.btn = tk.Button(self.root, text="Start Recording",
                             command=self.toggle_recording,
                             bg="#e1e1e1")
        self.btn.pack(pady=20)

    # ---------------------------
    # Recording toggle
    # ---------------------------
    def toggle_recording(self):
        global recording, chunk_thread

        recording = not recording

        if recording:
            self.btn.config(text="Stop Recording")
            self.status.config(text="Recording...", fg="#2ecc71")

            temps_buffer.clear()
            timestamps_buffer.clear()

            chunk_event.clear()

            chunk_thread = threading.Thread(
                target=save_buffer_worker,
                args=(
                    [],  # frames (empty)
                    timestamps_buffer,
                    temps_buffer,
                    chunk_event,
                    updates,
                    MAX_BUFFER,
                    API_URL,
                    None  # no img_lims
                ),
                daemon=True
            )
            chunk_thread.start()

        else:
            self.btn.config(text="Start Recording")
            self.status.config(text="Stopped", fg="#e74c3c")

            chunk_event.set()
            if chunk_thread:
                chunk_thread.join()

            filename = f"temps_{int(time.time())}.mp4"
            trigger_server_compilation("mp4", API_URL, filename)

    # ---------------------------
    # Main update loop
    # ---------------------------
    def update_loop(self):
        current_time = time.time() - self.start_time

        temps_now = []

        for i in range(NUM_PROBES):
            if USE_FAKE_TEMPS:
                raw = 15 + 4 * math.sin(
                    math.pi * ((i+1)/1.8) * current_time / 10
                )
            else:
                raw = 20  # replace with DAQ later

            temp = convert_temperature(raw)

            self.history[i].append(temp)
            avg = sum(self.history[i]) / len(self.history[i])

            self.temp_vars[i].set(f"{avg:.1f} °C")
            temps_now.append(avg)

        # ---- RECORDING ----
        if recording:
            timestamps_buffer.append(current_time)
            temps_buffer.append(temps_now)

        # UI refresh loop
        self.root.after(200, self.update_loop)

    def on_close(self):
        global recording

        recording = False
        chunk_event.set()

        self.root.destroy()
