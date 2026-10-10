"""Floating battery percentage overlay (top-right corner) for Windows.

Run:  pythonw battery_overlay.py   (no console window)
Close: double-click or right-click the overlay. Drag with left mouse to move.
"""
import ctypes
import tkinter as tk


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


def get_battery():
    status = SYSTEM_POWER_STATUS()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        return None, False
    pct = status.BatteryLifePercent
    if pct == 255:  # unknown / no battery
        return None, False
    return pct, status.ACLineStatus == 1


REFRESH_MS = 5000
MARGIN = 12

root = tk.Tk()
root.overrideredirect(True)          # no title bar
root.attributes("-topmost", True)    # always on top
root.attributes("-alpha", 0.85)      # slightly transparent
root.configure(bg="#1e1e1e")

label = tk.Label(root, font=("Segoe UI", 12, "bold"), fg="white", bg="#1e1e1e",
                 padx=10, pady=4)
label.pack()


def place_top_right():
    root.update_idletasks()
    x = root.winfo_screenwidth() - root.winfo_width() - MARGIN
    root.geometry(f"+{x}+{MARGIN}")


def refresh():
    pct, charging = get_battery()
    if pct is None:
        text, color = "🔋 N/A", "white"
    else:
        icon = "⚡" if charging else "🔋"
        text = f"{icon} {pct}%"
        color = "#4caf50" if pct > 50 else "#ffc107" if pct > 20 else "#f44336"
    label.config(text=text, fg=color)
    root.after(REFRESH_MS, refresh)


# Drag to move
def start_drag(e):
    root._dx, root._dy = e.x, e.y


def do_drag(e):
    root.geometry(f"+{e.x_root - root._dx}+{e.y_root - root._dy}")


label.bind("<Button-1>", start_drag)
label.bind("<B1-Motion>", do_drag)
label.bind("<Double-Button-1>", lambda e: root.destroy())
label.bind("<Button-3>", lambda e: root.destroy())

refresh()
place_top_right()
root.mainloop()
