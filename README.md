# nanoject-controller

Cross-platform GUI for controlling TTL pulse output on an Arduino-compatible
microcontroller (Arduino Uno/Mega/Nano, Teensy, etc.). Intended for triggering
a Drummond Nanoject (or any TTL-driven device) from a desktop computer.

## Features

- Specify number of pulses and inter-pulse interval, then click **Start**
- Live progress: pulses emitted / total, time elapsed / total
- **Stop** button (the Start button toggles to Stop while a sequence is running) to interrupt mid-sequence
- **Test** button for a single pulse, ignoring the other settings
- Output pin and pulse width are firmware constants (see [Firmware](#firmware))

## Repo layout

```
src/nanoject_controller/                              Python GUI + serial client
firmware/nanoject_controller/nanoject_controller.ino  MCU firmware
```

## Requirements

- Python 3.10+
- An Arduino-compatible board flashed with the firmware in `firmware/`
- Tkinter — bundled with python.org / Anaconda Python on macOS and Windows.
  On Linux, install the system package: `sudo apt install python3-tk`

## Install (computer side)

```bash
pip install git+https://github.com/calebweinreb/nanoject-controller.git
```

Or from a clone (recommended if you'll be tweaking settings):

```bash
git clone https://github.com/calebweinreb/nanoject-controller.git
cd nanoject-controller
pip install -e .
```

## Run

```bash
nanoject-controller
```

(equivalent to `python -m nanoject_controller`)

## Firmware

1. Open `firmware/nanoject_controller/nanoject_controller.ino` in the Arduino
   IDE (or PlatformIO). The Arduino IDE expects the `.ino` to live in a folder
   of the same name — that's why it's nested.
2. Adjust at the top of the file if needed:

   ```cpp
   const int  OUTPUT_PIN     = 8;    // TTL output pin
   const int  PULSE_WIDTH_MS = 10;   // pulse duration (ms)
   ```

3. Select your board / port in the IDE and upload.

The firmware works unchanged on standard Arduino boards and on Teensy. For
Teensy you'll need [Teensyduino](https://www.pjrc.com/teensy/teensyduino.html)
installed in the Arduino IDE.

## Usage

1. Plug the board in and launch the GUI.
2. Pick the serial port from the dropdown — click **Refresh** if you plugged
   the board in after launching:
   - macOS: `/dev/cu.usbmodem...`
   - Linux: `/dev/ttyACM0` or `/dev/ttyUSB0`
   - Windows: `COM3`, `COM4`, ...
3. Click **Connect**.
4. Set number of pulses and interval (ms), then **Start**. The button becomes
   **Stop** while running.
5. **Test** sends a single pulse on the configured pin at any time (ignores
   the number/interval fields).

## Linux serial-port permissions

If **Connect** fails with a permission error on Linux, add yourself to the
`dialout` group, then log out and back in:

```bash
sudo usermod -a -G dialout $USER
```

## Wire protocol (for reference)

ASCII, newline-terminated, 115200 baud.

| Direction    | Message                            |
|--------------|------------------------------------|
| host  -> MCU | `START <num_pulses> <interval_ms>` |
| host  -> MCU | `STOP`                             |
| host  -> MCU | `TEST`                             |
| host  -> MCU | `PING`                             |
| MCU  -> host | `READY` (once at boot)             |
| MCU  -> host | `OK` (generic ack)                 |
| MCU  -> host | `PULSE <n>` (after each pulse)     |
| MCU  -> host | `DONE` (sequence complete)         |
| MCU  -> host | `STOPPED` (sequence interrupted)   |
| MCU  -> host | `ERR <msg>`                        |
