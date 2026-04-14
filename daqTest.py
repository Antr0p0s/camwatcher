import tkinter as tk
from tkinter import messagebox
from mcculw import ul
from mcculw.enums import InterfaceType, TempScale
from mcculw.ul import ULError
from collections import deque

NUM_PROBES = 5

def convert_temperature(measured_temp):
    return 1.293 * measured_temp - 9.828

class TempMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MCCDAQ Temperature Monitor")
        self.root.geometry("400x450")
        self.root.configure(bg="#2c3e50")

        self.board_num = 0
        self.device_connected = False
        
        # Data storage for Moving Average (last 5 points per probe)
        self.history = [deque(maxlen=5) for _ in range(NUM_PROBES)]

        # UI Setup
        self.setup_ui()
        
        # Initialize DAQ and start loop immediately
        self.init_daq()
        if self.device_connected:
            self.update_temps()

    def setup_ui(self):
        # Header
        tk.Label(self.root, text="Thermal Probe Monitor", font=("Arial", 18, "bold"), 
                 bg="#2c3e50", fg="#ecf0f1").pack(pady=20)

        # Temperature Displays
        self.temp_vars = []
        
        # Using the specific colors you provided
        colors = ["#3399ff", "#000000", "#ff4d4d", "#ffffff", "#3cff01"]
        for i in range(NUM_PROBES):
            frame = tk.Frame(self.root, bg="#34495e", bd=2, relief="groove")
            frame.pack(pady=10, padx=40, fill="x")
            
            tk.Label(frame, text=f"Probe {i+1}:", font=("Arial", 12), 
                     bg="#34495e", fg="#bdc3c7").pack(side="left", padx=10)
            
            var = tk.StringVar(value="--.- °C")
            self.temp_vars.append(var)
            
            lbl = tk.Label(frame, textvariable=var, font=("Courier", 20, "bold"), 
                           bg="#34495e", fg=colors[i])
            lbl.pack(side="right", padx=10)

        self.status_lbl = tk.Label(self.root, text="Initializing...", bg="#2c3e50", fg="#95a5a6")
        self.status_lbl.pack(side="bottom", pady=20)

    def init_daq(self):
        try:
            devices = ul.get_daq_device_inventory(InterfaceType.ETHERNET)
            if not devices:
                self.status_lbl.config(text="Error: No Ethernet Device Found", fg="#e74c3c")
                return
            
            ul.create_daq_device(self.board_num, devices[0])
            self.device_connected = True
            self.status_lbl.config(text=f"Live: {devices[0].product_name}", fg="#2ecc71")
        except ULError as e:
            messagebox.showerror("DAQ Error", f"Initialization failed: {e.message}")

    def update_temps(self):
        try:
            for i in range(NUM_PROBES):
                # 1. Read raw temperature
                raw_temp = ul.t_in(self.board_num, i, TempScale.CELSIUS)
                
                # 2. Add to history
                self.history[i].append(convert_temperature(raw_temp))
                
                # 3. Calculate Moving Average
                avg_temp = sum(self.history[i]) / len(self.history[i])
                
                # 4. Update UI Variable
                self.temp_vars[i].set(f"{round(avg_temp, 1)} °C")
            
            # Schedule next update in 1000ms
            self.root.after(1000, self.update_temps)
            
        except ULError as e:
            self.status_lbl.config(text="Hardware Connection Lost", fg="#e74c3c")
            messagebox.showerror("Read Error", f"Hardware error: {e.message}")

    def on_closing(self):
        if self.device_connected:
            ul.release_daq_device(self.board_num)
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TempMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()