"""Floating overlays for Windows: network speed + battery percentage
(top-right corner) and a digital clock (top-left corner).

Requires: pip install psutil

Run:  pythonw battery_overlay.py   (no console window)
The overlays are click-through: mouse clicks pass to the windows behind them.
Running it again while the overlays are shown closes them (toggle).
"""
import ctypes
import ctypes.wintypes as wintypes
import threading
import time
import tkinter as tk

import psutil

# Toggle: if an instance is already running, tell it to quit and exit.
kernel32 = ctypes.windll.kernel32
kernel32.CreateMutexW.restype = ctypes.c_void_p
kernel32.CreateEventW.restype = ctypes.c_void_p
ERROR_ALREADY_EXISTS = 183
_mutex = kernel32.CreateMutexW(None, False, "Local\\BatteryOverlayMutex")
already_running = kernel32.GetLastError() == ERROR_ALREADY_EXISTS
quit_event = kernel32.CreateEventW(None, True, False, "Local\\BatteryOverlayQuit")
if already_running:
    kernel32.SetEvent(ctypes.c_void_p(quit_event))
    raise SystemExit
kernel32.ResetEvent(ctypes.c_void_p(quit_event))


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
CLOCK_FORMAT = "%d/%m/%Y   %H:%M:%S"
MARGIN = 0
IDLE_ALPHA = 0.25                    # 0.0 = invisible, 1.0 = opaque
ACTIVE_ALPHA = 1.0                   # on mouse hover / swipe from the top edge
REVEAL_MS = 3000                     # how long a top-edge swipe keeps them visible
TOP_EDGE_PX = 1                      # mouse cursor this close to the top = reveal
SWIPE_START = 0.03                   # touch must start in the top 3% of the screen...
SWIPE_DISTANCE = 0.08                # ...and move down at least 8% of the screen height
BG = "#1e1e1e"


def make_overlay(win):
    win.overrideredirect(True)          # no title bar
    win.attributes("-topmost", True)    # always on top
    win.attributes("-alpha", IDLE_ALPHA)
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


# Reveal: fade to full opacity while the cursor is over an overlay, or for a
# few seconds after the cursor/touch hits the top screen edge (swipe down).
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


alpha = {root: IDLE_ALPHA, clock_win: IDLE_ALPHA}
reveal_until = 0.0
LWA_ALPHA = 0x2


def set_alpha(win, value):
    # Set directly: Tk's "-alpha" 1.0 drops WS_EX_LAYERED, which would end click-through.
    hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
    ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, int(value * 255), LWA_ALPHA)


def watch_cursor():
    global reveal_until
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    now = time.monotonic()
    if pt.y <= TOP_EDGE_PX:
        reveal_until = now + REVEAL_MS / 1000
    for win in alpha:
        x, y = win.winfo_rootx(), win.winfo_rooty()
        hover = x <= pt.x < x + win.winfo_width() and y <= pt.y < y + win.winfo_height()
        target = ACTIVE_ALPHA if hover or now < reveal_until else IDLE_ALPHA
        current = alpha[win]
        if current != target:  # smooth fade
            step = 0.15 if target > current else 0.05
            current = min(target, current + step) if target > current else max(target, current - step)
            alpha[win] = current
            set_alpha(win, current)
    root.after(30, watch_cursor)


# Touch swipe from the top edge. Touch input doesn't move the cursor, so read
# the touchscreen directly via Raw Input (works while other apps have focus).
user32 = ctypes.windll.user32
hid = ctypes.windll.hid
user32.CreateWindowExW.restype = ctypes.c_void_p
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
user32.GetRawInputData.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p,
                                   ctypes.POINTER(ctypes.c_uint), ctypes.c_uint]
user32.GetRawInputDeviceInfoW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p,
                                          ctypes.POINTER(ctypes.c_uint)]
HIDP_OK = 0x00110000
VALUE_CAPS_SIZE = 72


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", ctypes.c_ushort), ("usUsage", ctypes.c_ushort),
                ("dwFlags", wintypes.DWORD), ("hwndTarget", ctypes.c_void_p)]


class DEVMODEW(ctypes.Structure):  # only the fields up to dmDisplayOrientation
    _fields_ = [("dmDeviceName", ctypes.c_wchar * 32), ("dmSpecVersion", wintypes.WORD),
                ("dmDriverVersion", wintypes.WORD), ("dmSize", wintypes.WORD),
                ("dmDriverExtra", wintypes.WORD), ("dmFields", wintypes.DWORD),
                ("dmPositionX", ctypes.c_long), ("dmPositionY", ctypes.c_long),
                ("dmDisplayOrientation", wintypes.DWORD), ("dmDisplayFixedOutput", wintypes.DWORD),
                ("_rest", ctypes.c_byte * 200)]


def screen_orientation():
    dm = DEVMODEW()
    dm.dmSize = ctypes.sizeof(DEVMODEW)
    user32.EnumDisplaySettingsW(None, -1, ctypes.byref(dm))  # ENUM_CURRENT_SETTINGS
    return dm.dmDisplayOrientation  # 0, 1 (90°), 2 (180°), 3 (270°)


def touch_to_screen_y(x, y, orientation):
    """Digitizer position (0..1) -> distance from the top of the screen (0..1)."""
    return (y, x, 1 - y, 1 - x)[orientation]


def logical_max(caps, i):
    return max(int.from_bytes(caps[i * VALUE_CAPS_SIZE + 44:i * VALUE_CAPS_SIZE + 48], "little", signed=True), 1)


def axis_caps(pp, usage):
    """{link collection (one per finger): logical max} for X (0x30) or Y (0x31)."""
    n = ctypes.c_ushort(64)
    buf = ctypes.create_string_buffer(VALUE_CAPS_SIZE * 64)
    hid.HidP_GetSpecificValueCaps(0, 0x01, 0, usage, buf, ctypes.byref(n), pp)
    raw = buf.raw
    return {int.from_bytes(raw[i * VALUE_CAPS_SIZE + 6:i * VALUE_CAPS_SIZE + 8], "little"): logical_max(raw, i)
            for i in range(n.value)}


devices = {}   # raw device handle -> (preparsed data, x caps, y caps)
contacts = {}  # finger (link collection) -> [start screen y, already triggered]


def device_info(hdev):
    if hdev not in devices:
        size = ctypes.c_uint(0)
        user32.GetRawInputDeviceInfoW(hdev, 0x20000005, None, ctypes.byref(size))  # RIDI_PREPARSEDDATA
        pp = ctypes.create_string_buffer(size.value)
        user32.GetRawInputDeviceInfoW(hdev, 0x20000005, pp, ctypes.byref(size))
        devices[hdev] = (pp, axis_caps(pp, 0x30), axis_caps(pp, 0x31))
    return devices[hdev]


def handle_touch_report(pp, xcaps, ycaps, report):
    global reveal_until
    rbuf = ctypes.create_string_buffer(report, len(report))
    for link, ymax in ycaps.items():
        xv, yv = ctypes.c_ulong(), ctypes.c_ulong()
        if hid.HidP_GetUsageValue(0, 0x01, link, 0x31, ctypes.byref(yv), pp, rbuf, len(report)) != HIDP_OK:
            continue
        hid.HidP_GetUsageValue(0, 0x01, link, 0x30, ctypes.byref(xv), pp, rbuf, len(report))
        usages = (ctypes.c_ushort * 16)()
        count = ctypes.c_ulong(16)
        tip = (hid.HidP_GetUsages(0, 0x0D, link, usages, ctypes.byref(count), pp, rbuf, len(report)) == HIDP_OK
               and 0x42 in usages[:count.value])  # Tip Switch = finger touching
        if not tip:
            contacts.pop(link, None)
            continue
        y = touch_to_screen_y(xv.value / xcaps.get(link, 1), yv.value / ymax, screen_orientation())
        if link not in contacts:
            contacts[link] = [y, False]
        start, triggered = contacts[link]
        if not triggered and start <= SWIPE_START and y - start >= SWIPE_DISTANCE:
            contacts[link][1] = True
            reveal_until = time.monotonic() + REVEAL_MS / 1000


def handle_raw_input(hraw):
    size = ctypes.c_uint(0)
    user32.GetRawInputData(hraw, 0x10000003, None, ctypes.byref(size), 24)  # RID_INPUT
    buf = ctypes.create_string_buffer(size.value)
    user32.GetRawInputData(hraw, 0x10000003, buf, ctypes.byref(size), 24)
    data = buf.raw
    if int.from_bytes(data[0:4], "little") != 2:  # RIM_TYPEHID
        return
    pp, xcaps, ycaps = device_info(int.from_bytes(data[8:16], "little"))
    report_size = int.from_bytes(data[24:28], "little")
    for k in range(int.from_bytes(data[28:32], "little")):
        handle_touch_report(pp, xcaps, ycaps, data[32 + k * report_size:32 + (k + 1) * report_size])


def watch_touch():
    # Runs in its own thread with a hidden window that receives WM_INPUT.
    hwnd = user32.CreateWindowExW(0, "STATIC", "BatteryOverlayTouch", 0, 0, 0, 0, 0,
                                  None, None, None, None)
    device = RAWINPUTDEVICE(0x0D, 0x04, 0x100, hwnd)  # Digitizer/Touch Screen, RIDEV_INPUTSINK
    if not user32.RegisterRawInputDevices(ctypes.byref(device), 1, ctypes.sizeof(RAWINPUTDEVICE)):
        return  # no touchscreen
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == 0x00FF:  # WM_INPUT
            try:
                handle_raw_input(ctypes.c_void_p(msg.lParam))
            except Exception:
                pass
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


def watch_quit():
    if kernel32.WaitForSingleObject(ctypes.c_void_p(quit_event), 0) == 0:  # signaled
        root.destroy()
        return
    root.after(300, watch_quit)


clock_win.geometry(f"+{MARGIN}+{MARGIN}")
watch_quit()
watch_cursor()
threading.Thread(target=watch_touch, daemon=True).start()
refresh()
tick()
make_click_through(root)
make_click_through(clock_win)
root.mainloop()
