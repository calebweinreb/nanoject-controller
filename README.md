# nanoject-controller

GUI for triggering a Drummond Nanoject from a desktop computer. The host
computer talks over USB serial to an Arduino/Teensy, which drives an
optocoupler that closes the contacts of the Nanoject's foot-pedal input —
each MCU pulse is one foot-pedal "press."

## Usage

1. Plug the board in and launch the GUI:

   ```
   nanoject-controller
   ```

2. Pick the serial port from the dropdown (Refresh if you plugged in after
   launching) and click **Connect**.
3. Set number of pulses and interval (ms), then **Start**. The button toggles
   to **Stop** while running.
4. **Test** fires a single pulse, ignoring the other fields.

Output pin and pulse width are firmware constants — edit them at the top of
the `.ino`.

## Install

Requires Python 3.10+ and an Arduino-compatible board flashed with the
firmware in `firmware/`. On Linux, also: `sudo apt install python3-tk`.

```bash
git clone https://github.com/calebweinreb/nanoject-controller.git
cd nanoject-controller
pip install -e .
```

### Firmware

Open `firmware/nanoject_controller/nanoject_controller.ino` in the Arduino
IDE, pick your board and port, and upload. Teensy boards need
[Teensyduino](https://www.pjrc.com/teensy/teensyduino.html) installed.

### Linux serial-port permissions

If **Connect** fails with a permission error, add yourself to `dialout` and
log out / back in:

```bash
sudo usermod -a -G dialout $USER
```
