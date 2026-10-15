# battery-overlay

Small always-on-top overlays for Windows, written in Python/tkinter:

- **Top-right:** real-time network download/upload speed and battery percentage
  (green > 50%, yellow > 20%, red below; ⚡ while charging)
- **Top-left:** digital clock

![Overlays on top of a game (Genshin Impact)](screenshots/in-game.jpg)

![Network speed and battery overlay](screenshots/battery-network.png)
![Clock overlay](screenshots/clock.png)

The overlays stay faint until you need them: they fade to full opacity while
the mouse is over one, and both show for a few seconds after the mouse hits the
top edge of the screen or you **swipe down from the top edge** on a touchscreen.
Touch is read directly from the touchscreen (Raw Input), so the swipe works even
while a game or another app has focus, and it follows the screen rotation.

They are also **click-through**: mouse clicks go to the
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

Running it again while the overlays are shown **closes them**, so the same
command (or shortcut) works as an on/off toggle.

`pythonw` runs without a console window and hides errors. Use
`python battery_overlay.py` if something doesn't show up.

## Desktop / Start Menu shortcut

Create a shortcut (on the Desktop, in the Start Menu, or in `shell:startup` to
start at login) with:

- **Target:** `"C:\path\to\pythonw.exe" "C:\path\to\battery_overlay.py"`
- **Start in:** the folder containing `battery_overlay.py`
- **Icon:** `icon.ico` from this repo

Click it once to show the overlays, click it again to hide them.

## Settings

Edit the constants near the top of `battery_overlay.py`:

| Setting | Default | Meaning |
|---|---|---|
| `IDLE_ALPHA` | `0.25` | Normal opacity, `0.0` invisible to `1.0` opaque |
| `ACTIVE_ALPHA` | `1.0` | Opacity on hover or after a swipe from the top |
| `REVEAL_MS` | `3000` | How long a swipe from the top keeps the overlays visible |
| `SWIPE_START` | `0.03` | A touch swipe must start within this fraction of the top of the screen |
| `SWIPE_DISTANCE` | `0.08` | ...and move down at least this fraction of the screen height |
| `MARGIN` | `0` | Distance from screen edges in pixels |
| `CLOCK_FORMAT` | `"%d/%m/%Y   %H:%M:%S"` | Date/time format, e.g. `"%H:%M"` or `"%d %b %Y   %I:%M %p"` |
| `REFRESH_MS` | `1000` | Battery and network update interval |
