"""Floating battery percentage overlay (top-right corner) for Windows.

Run:  pythonw battery_overlay.py   (no console window)
The overlay is click-through: mouse clicks pass to the windows behind it.
Close: end "pythonw.exe" in Task Manager.
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
    place_top_right()  # keep right edge aligned when text width changes
    root.after(REFRESH_MS, refresh)


# Click-through: let mouse input pass to windows behind the overlay
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080   # hide from taskbar / Alt+Tab
WS_EX_NOACTIVATE = 0x08000000   # never steal focus


def make_click_through():
    user32 = ctypes.windll.user32
    hwnd = user32.GetParent(root.winfo_id())
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


refresh()
make_click_through()
root.mainloop()
