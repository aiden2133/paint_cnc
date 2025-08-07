import tkinter as tk
from tkinter import ttk
import serial
import time
#from gcode_sender import send_gcode_line, setup_grbl, send_gcode_file

SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200
DEBUG_MODE = True

class JogController:
    def __init__(self, debug=False):
        self.debug = debug
        self.ser = None
        self.feedrate = 1000
        self.step_size = 1.0

        if not self.debug:
            try:
                self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
                time.sleep(2)
                self.ser.reset_input_buffer()
                send_gcode_line(self.ser, "G91")  # relative positioning
            except Exception as e:
                print(f"Serial connection failed: {e}")
                self.debug = True

    def send(self, cmd):
        if self.debug:
            print(f"[DEBUG] Would send: {cmd}")
            return f"[DEBUG] {cmd}"
        else:
            return send_gcode_line(self.ser, cmd)

    def send_file(self, filepath):
        if self.debug:
            print(f"[DEBUG] Would send file: {filepath}")
            return f"[DEBUG] Sending file: {filepath}"
        else:
            send_gcode_file(filepath)
            return f"Sent file: {filepath}"

    def jog(self, axis, direction):
        distance = self.step_size * direction
        cmd = f"$J=G91 {axis}{distance} F{self.feedrate}"
        return self.send(cmd)

    def home(self):
        return self.send("$H")

    def reset(self):
        if self.debug:
            print("[DEBUG] Would send: Soft Reset")
            return "[DEBUG] Soft Reset"
        self.ser.write(b'\x18')
        self.ser.flush()
        time.sleep(1)
        self.ser.reset_input_buffer()
        return self.send("$X")

    def zero_all(self):
        return self.send("G10 L20 P1 X0 Y0 Z0")

    def send_gcode(self, cmd):
        return self.send(cmd)

    def send_file(self, filepath):
        if self.debug:
            print(f"[DEBUG] Would send file: {filepath}")
        else:
            send_gcode_file(filepath)

    def setup(self):
        if not self.debug:
            setup_grbl(self.ser)
        else:
            print("[DEBUG] Setup called")

    def close(self):
        if self.ser:
            self.ser.close()

class JogGUI:
    def __init__(self, root):
        self.controller = JogController(debug=DEBUG_MODE)

        root.title("GRBL Jog Controller")
        self.create_widgets(root)

    def create_widgets(self, root):
        frame = ttk.Frame(root, padding=10)
        frame.grid(row=0, column=0)

        # --- Feedrate input ---
        ttk.Label(frame, text="Feedrate (mm/min):").grid(row=0, column=0, sticky="w")
        self.feedrate_var = tk.StringVar(value="1000")
        self.feedrate_entry = ttk.Entry(frame, textvariable=self.feedrate_var, width=10)
        self.feedrate_entry.grid(row=0, column=1, sticky="w")
        ttk.Button(frame, text="Set", command=self.set_feedrate).grid(row=0, column=2, sticky="w")

        # --- Step size input ---
        ttk.Label(frame, text="Step Size (mm):").grid(row=1, column=0, sticky="w")
        self.step_var = tk.StringVar(value="1.0")
        self.step_entry = ttk.Entry(frame, textvariable=self.step_var, width=10)
        self.step_entry.grid(row=1, column=1, sticky="w")
        ttk.Button(frame, text="Set", command=self.set_step).grid(row=1, column=2, sticky="w")

        # --- Movement controls frame ---
        jog_frame = ttk.Frame(frame, padding=(0, 10))
        jog_frame.grid(row=2, column=0, columnspan=3)

        # Z axis on the left
        ttk.Button(jog_frame, text="↑ Z+", width=6, command=lambda: self.jog("Z", 1)).grid(row=0, column=0, rowspan=1,
                                                                                           padx=5, pady=2)
        ttk.Button(jog_frame, text="↓ Z-", width=6, command=lambda: self.jog("Z", -1)).grid(row=1, column=0, rowspan=1,
                                                                                            padx=5, pady=2)

        # XY cross layout
        ttk.Button(jog_frame, text="↑ Y+", width=6, command=lambda: self.jog("Y", 1)).grid(row=0, column=1,
                                                                                           columnspan=2)
        ttk.Button(jog_frame, text="← X-", width=6, command=lambda: self.jog("X", -1)).grid(row=1, column=1)
        ttk.Button(jog_frame, text="→ X+", width=6, command=lambda: self.jog("X", 1)).grid(row=1, column=2)
        ttk.Button(jog_frame, text="↓ Y-", width=6, command=lambda: self.jog("Y", -1)).grid(row=2, column=1,
                                                                                            columnspan=2)

        # Stop/resume button centered under
        ttk.Button(jog_frame, text="⏹ Stop", command=self.stop_movement).grid(row=3, column=1, columnspan=2,
                                                                              pady=(5, 0))

        # --- Command buttons ---
        ttk.Button(frame, text="Home ($H)", command=self.controller.home).grid(row=3, column=0, columnspan=3,
                                                                               sticky="ew")
        ttk.Button(frame, text="Reset", command=self.controller.reset).grid(row=4, column=0, columnspan=3, sticky="ew")
        ttk.Button(frame, text="Zero All", command=self.controller.zero_all).grid(row=5, column=0, columnspan=3,
                                                                                  sticky="ew")
        ttk.Button(frame, text="Setup", command=self.controller.setup).grid(row=6, column=0, columnspan=3, sticky="ew")

        # --- Manual G-code input ---
        self.manual_entry = ttk.Entry(frame)
        self.manual_entry.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Button(frame, text="Send GCODE", command=self.send_manual_gcode).grid(row=8, column=0, columnspan=3,
                                                                                  sticky="ew")
        # --- G-code file path entry ---
        self.file_path_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.file_path_var).grid(row=9, column=0, columnspan=2, sticky="ew")
        ttk.Button(frame, text="Send File", command=self.send_file).grid(row=9, column=2, sticky="ew")

        # --- Status label (moved below) ---
        self.status = tk.StringVar()
        self.status.set("Ready")
        ttk.Label(frame, textvariable=self.status).grid(row=10, column=0, columnspan=3, pady=5)

    def set_feedrate(self):
        try:
            val = float(self.feedrate_var.get())
            self.controller.feedrate = val
            self.status.set(f"Feedrate set to {val}")
        except ValueError:
            self.status.set("Invalid feedrate value")

    def stop_movement(self):
        if self.controller.debug:
            print("[DEBUG] Would send: ~ (resume/stop)")
            self.status.set("[DEBUG] Stop (~) sent")
        else:
            self.controller.ser.write(b'~')
            self.controller.ser.flush()
            self.status.set("Stop (~) sent")

    def set_step(self):
        try:
            val = float(self.step_var.get())
            self.controller.step_size = val
            self.status.set(f"Step size set to {val}")
        except ValueError:
            self.status.set("Invalid step size value")


    def update_feedrate(self, val):
        self.controller.feedrate = float(val)

    def update_step(self, val):
        self.controller.step_size = float(val)

    def jog(self, axis, direction):
        response = self.controller.jog(axis, direction)
        self.status.set(response)

    def send_manual_gcode(self):
        cmd = self.manual_entry.get().strip()
        if cmd:
            response = self.controller.send_gcode(cmd)
            self.status.set(response)

    def send_file(self):
        filepath = self.file_path_var.get().strip()
        if filepath:
            response = self.controller.send_file(filepath)
            self.status.set(response)
        else:
            self.status.set("Please enter a G-code file path")

    def on_close(self):
        self.controller.close()
        root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = JogGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()