"""Serial communication with the nanoject MCU firmware."""
from __future__ import annotations

import queue
import threading
import time

import serial
from serial.tools import list_ports


def list_serial_ports() -> list[str]:
    return [p.device for p in list_ports.comports()]


class Controller:
    """Background-threaded serial client for the nanoject firmware.

    Events from the MCU are pushed onto self.events as dicts:
      {"type": "ready"}
      {"type": "ok"}
      {"type": "pulse", "n": int}
      {"type": "done"}
      {"type": "stopped"}
      {"type": "error", "msg": str}
      {"type": "raw", "line": str}
      {"type": "disconnect"}
    """

    def __init__(self, port: str, baud: int = 115200, timeout: float = 0.1):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.events: queue.Queue = queue.Queue()
        self._ser: serial.Serial | None = None
        self._stop = threading.Event()
        self._reader: threading.Thread | None = None

    def open(self) -> None:
        self._ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        # Many Arduino-like boards reset on serial open; give the bootloader time.
        time.sleep(2.0)
        self._stop.clear()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def close(self) -> None:
        self._stop.set()
        if self._reader is not None:
            self._reader.join(timeout=1.0)
            self._reader = None
        if self._ser is not None:
            try:
                self._ser.close()
            finally:
                self._ser = None

    def start_sequence(self, num_pulses: int, interval_ms: int) -> None:
        self._send(f"START {num_pulses} {interval_ms}")

    def stop(self) -> None:
        self._send("STOP")

    def test_pulse(self) -> None:
        self._send("TEST")

    def _send(self, line: str) -> None:
        if self._ser is None:
            raise RuntimeError("not connected")
        self._ser.write((line + "\n").encode("ascii"))
        self._ser.flush()

    def _read_loop(self) -> None:
        buf = b""
        while not self._stop.is_set() and self._ser is not None:
            try:
                data = self._ser.read(64)
            except (serial.SerialException, OSError):
                self.events.put({"type": "disconnect"})
                return
            if not data:
                continue
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                self._dispatch(line.decode("ascii", errors="replace").strip())

    def _dispatch(self, line: str) -> None:
        if not line:
            return
        if line == "READY":
            self.events.put({"type": "ready"})
        elif line == "OK":
            self.events.put({"type": "ok"})
        elif line == "DONE":
            self.events.put({"type": "done"})
        elif line == "STOPPED":
            self.events.put({"type": "stopped"})
        elif line.startswith("PULSE "):
            try:
                n = int(line.split()[1])
                self.events.put({"type": "pulse", "n": n})
            except (ValueError, IndexError):
                self.events.put({"type": "raw", "line": line})
        elif line.startswith("ERR"):
            self.events.put({"type": "error", "msg": line})
        else:
            self.events.put({"type": "raw", "line": line})
