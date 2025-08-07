import tkinter as tk
from tkinter import messagebox
import numpy as np
import tkinter.font as tkfont

PIXEL_SIZE = 10
ROWS = 50
COLS = 40

color_map = {
    0: 'red',
    1: 'yellow',
    2: 'blue',
    3: '#4B0082',
    4: '#90EE90',
    5: 'black',
    6: 'gray',
    7: '#8A3324',
    8: '#FF6100',
    9: '#006400',
    10: 'white',
}

class PaintCNCApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CNC Paint Designer")

        self.canvas_data = np.full((ROWS, COLS), 10)  # default white
        self.current_color_id = 0

        self.paint_history = []  # Stack for undo: store (i, j, old_color_id)

        self.canvas = tk.Canvas(root, width=COLS * PIXEL_SIZE, height=ROWS * PIXEL_SIZE)
        self.canvas.pack(side=tk.LEFT)

        self.rects = [[None for _ in range(COLS)] for _ in range(ROWS)]
        for i in range(ROWS):
            for j in range(COLS):
                x0, y0 = j * PIXEL_SIZE, i * PIXEL_SIZE
                x1, y1 = x0 + PIXEL_SIZE, y0 + PIXEL_SIZE
                rect = self.canvas.create_rectangle(x0, y0, x1, y1, fill=color_map[10], outline="")
                self.rects[i][j] = rect

        self.canvas.bind("<Button-1>", self.paint_pixel)
        self.canvas.bind("<B1-Motion>", self.paint_pixel)

        self.palette_frame = tk.Frame(root)
        self.palette_frame.pack(side=tk.RIGHT, padx=10)

        tk.Label(self.palette_frame, text="Select Color:").pack(pady=5)

        self.color_labels = {
            0: 'RED',
            1: 'YELLOW',
            2: 'BLUE',
            3: 'INDIGO',
            4: 'LIGHT GREEN',
            5: 'BLACK',
            6: 'GRAY',
            7: 'BROWN',
            8: 'ORANGE',
            9: 'DARK GREEN',
            10: 'WHITE',
        }

        self.color_buttons = {}  # store buttons for later update

        for color_id, color in color_map.items():
            btn = tk.Button(
                self.palette_frame,
                bg=color,
                activebackground=color,
                fg="black",  # force black text for all
                text=self.color_labels[color_id],
                relief=tk.RAISED,
                highlightthickness=1,
                bd=1,
                padx=5,
                pady=5,
                command=lambda cid=color_id: self.set_color(cid)
            )
            btn.pack(pady=3, fill='x')
            self.color_buttons[color_id] = btn

        # Initially highlight the selected color button
        self.update_color_buttons()

        tk.Button(self.palette_frame, text="Undo", command=self.undo_paint).pack(pady=5)

        # Add filename label and entry before Export button
        tk.Label(self.palette_frame, text="Filename:").pack(pady=(20, 2))
        self.filename_entry = tk.Entry(self.palette_frame)
        self.filename_entry.insert(0, "paint_canvas.gcode")  # default filename
        self.filename_entry.pack(pady=(0, 10), fill='x')

        tk.Button(self.palette_frame, text="Export G-code", command=self.export_gcode).pack(pady=5)
        tk.Button(self.palette_frame, text="Clear Canvas", command=self.clear_canvas).pack(pady=5)

    def set_color(self, color_id):
        self.current_color_id = color_id
        self.update_color_buttons()

    def update_color_buttons(self):
        # Highlight selected color button, others normal
        for cid, btn in self.color_buttons.items():
            if cid == self.current_color_id:
                btn.config(relief=tk.SUNKEN, bd=3)
            else:
                btn.config(relief=tk.RAISED, bd=1)

    def paint_pixel(self, event):
        j = event.x // PIXEL_SIZE
        i = event.y // PIXEL_SIZE
        if 0 <= i < ROWS and 0 <= j < COLS:
            old_color = self.canvas_data[i, j]
            new_color = self.current_color_id
            if old_color != new_color:
                self.paint_history.append((i, j, old_color))  # Save for undo
                self.canvas_data[i, j] = new_color
                self.canvas.itemconfig(self.rects[i][j], fill=color_map[new_color])

    def undo_paint(self):
        if self.paint_history:
            i, j, old_color = self.paint_history.pop()
            self.canvas_data[i, j] = old_color
            self.canvas.itemconfig(self.rects[i][j], fill=color_map[old_color])
        else:
            messagebox.showinfo("Undo", "Nothing to undo.")

    def clear_canvas(self):
        self.canvas_data.fill(10)
        self.paint_history.clear()
        for i in range(ROWS):
            for j in range(COLS):
                self.canvas.itemconfig(self.rects[i][j], fill=color_map[10])

    def export_gcode(self):
        filename = self.filename_entry.get().strip()
        if not filename:
            filename = "paint_canvas.gcode"
        if not filename.lower().endswith(".gcode"):
            filename += ".gcode"

        gcode_lines = generate_pointillism_gcode(self.canvas_data)
        try:
            import os
            os.makedirs("output", exist_ok=True)
            filepath = f"output/{filename}"
            with open(filepath, "w") as f:
                f.write("\n".join(gcode_lines))
            messagebox.showinfo("Success", f"G-code saved to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


def generate_pointillism_gcode(color_matrix, feedrate=800, z_height=0):
    gcode = [
        "G90",
        "G10 L20 P1 X0 Y0 Z0",
        "G1 Z3 F500",
        "G0 X-100 F800",
        "M0 ; Pause to change color"
    ]

    rows = color_matrix.shape[0]  # 50
    cols = color_matrix.shape[1]  # 40

    start_x = 2.5    # mm, positive increasing X start
    start_y = -2.5   # mm, negative decreasing Y start
    step = 5         # mm per pixel
    vertical_color_spacing = 5  # vertical gap per color block

    for color_index in range(10):
        gcode.append(f"; --- Starting color: {color_map[color_index]} ---")

        # vertical offset pushes the whole block further down (more negative)
        color_y_offset = -vertical_color_spacing * color_index

        for i in range(rows):
            for j in range(cols):
                if int(color_matrix[i, j]) == color_index:
                    x_pos = start_x + j * step
                    y_pos = start_y - i * step + color_y_offset  # negative Y, going down

                    gcode.append(f"G0 X{x_pos:.2f} F{feedrate}")
                    gcode.append(f"G0 Y{y_pos:.2f} F{feedrate}")
                    gcode.append(";DISPENSE")
                    gcode.append(f"G1 Z{z_height:.2f} F500")
                    gcode.append("G1 Z3 F500")

        gcode.append("G1 Z5 F1000")
        gcode.append("G0 X-100 F800")
        gcode.append("G0 Y0 F800")
        gcode.append("M0 ; Pause to change color")

    return gcode



if __name__ == "__main__":
    import os
    os.makedirs("output", exist_ok=True)
    root = tk.Tk()
    app = PaintCNCApp(root)
    root.mainloop()
