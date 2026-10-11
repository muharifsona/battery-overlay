# battery-overlay

Small always-on-top overlays for Windows, written in Python/tkinter:

- **Top-right:** real-time network download/upload speed and battery percentage
  (green > 50%, yellow > 20%, red below; ⚡ while charging)
- **Top-left:** digital clock

![Network speed and battery overlay](screenshots/battery-network.png)
![Clock overlay](screenshots/clock.png)

The overlays are semi-transparent and **click-through**: mouse clicks go to the
windows behind them, they never take focus, and they don't show up in the
taskbar or Alt+Tab.

## Requirements

- Windows
- Python 3.8+
- [psutil](https://pypi.org/project/psutil/)

```bash
pip install psutil
```

## Run

```bash
pythonw battery_overlay.py
```

`pythonw` runs without a console window and hides errors. Use
`python battery_overlay.py` if something doesn't show up.

To close the overlays, end `pythonw.exe` in Task Manager.

## Start automatically at login

Press <kbd>Win</kbd>+<kbd>R</kbd>, open `shell:startup`, and create a shortcut there with:

- **Target:** `"C:\path\to\pythonw.exe" "C:\path\to\battery_overlay.py"`
- **Start in:** the folder containing `battery_overlay.py`

## Settings

Edit the constants near the top of `battery_overlay.py`:

| Setting | Default | Meaning |
|---|---|---|
| `ALPHA` | `0.5` | Opacity, `0.0` invisible to `1.0` opaque |
| `MARGIN` | `0` | Distance from screen edges in pixels |
| `CLOCK_FORMAT` | `"%H:%M:%S"` | Clock format, e.g. `"%H:%M"` or `"%I:%M %p"` |
| `REFRESH_MS` | `1000` | Battery and network update interval |
