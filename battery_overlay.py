"""Floating overlays for Windows: network speed + battery percentage
(top-right corner) and a digital clock (top-left corner).

Requires: pip install psutil

Run:  pythonw battery_overlay.py   (no console window)
The overlays are click-through: mouse clicks pass to the windows behind them.
Close: end "pythonw.exe" in Task Manager.
"""
import ctypes
import time
import tkinter as tk

import psutil


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


def format_speed(bytes_per_sec):
    for unit in ("B/s", "KB/s", "MB/s"):
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} {unit}" if unit == "B/s" else f"{bytes_per_sec:.1f} {unit}"
        bytes_per_sec /= 1024
    return f"{bytes_per_sec:.1f} GB/s"


REFRESH_MS = 1000
CLOCK_FORMAT = "%H:%M:%S"
MARGIN = 0
ALPHA = 0.5                          # 0.0 = invisible, 1.0 = opaque
BG = "#1e1e1e"


def make_overlay(win):
    win.overrideredirect(True)          # no title bar
    win.attributes("-topmost", True)    # always on top
    win.attributes("-alpha", ALPHA)
    win.configure(bg=BG)
    label = tk.Label(win, font=("Segoe UI", 12, "bold"), fg="white", bg=BG,
                     padx=10, pady=4)
    label.pack()
    return label


root = tk.Tk()                       # network speed + battery overlay
label = make_overlay(root)
label.pack(side="right")
net_label = tk.Label(root, font=("Segoe UI", 12, "bold"), fg="white", bg=BG,
                     padx=10, pady=4)
net_label.pack(side="right")
clock_win = tk.Toplevel(root)        # clock overlay
clock_label = make_overlay(clock_win)


def place_top_right():
    root.update_idletasks()
    x = root.winfo_screenwidth() - root.winfo_width() - MARGIN
    root.geometry(f"+{x}+{MARGIN}")


last_net = (psutil.net_io_counters(), time.monotonic())


def refresh():
    global last_net
    counters, now = psutil.net_io_counters(), time.monotonic()
    prev, prev_time = last_net
    elapsed = max(now - prev_time, 1e-6)
    down = (counters.bytes_recv - prev.bytes_recv) / elapsed
    up = (counters.bytes_sent - prev.bytes_sent) / elapsed
    last_net = (counters, now)
    net_label.config(text=f"↓ {format_speed(down)}   ↑ {format_speed(up)}")

    pct, charging = get_battery()
    if pct is None:
        text, color = "🔋 N/A", "white"
    else:
        icon = "⚡" if charging else "🔋"
        text = f"{icon} {pct}%"
        color = "#4caf50" if pct > 50 else "#ffc107" if pct > 20 else "#f44336"
    label.config(text=text, fg=color)
    place_top_right()  # keep right edge aligned when text width changes
    root.after(REFRESH_MS, refresh)


def tick():
    clock_label.config(text=time.strftime(CLOCK_FORMAT))
    # schedule next update right after the next full second
    root.after(1000 - int(time.time() * 1000) % 1000 + 5, tick)


# Click-through: let mouse input pass to windows behind the overlay
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080   # hide from taskbar / Alt+Tab
WS_EX_NOACTIVATE = 0x08000000   # never steal focus


def make_click_through(win):
    win.update_idletasks()
    user32 = ctypes.windll.user32
    hwnd = user32.GetParent(win.winfo_id())
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


clock_win.geometry(f"+{MARGIN}+{MARGIN}")
refresh()
tick()
make_click_through(root)
make_click_through(clock_win)
root.mainloop()
