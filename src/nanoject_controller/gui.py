"""Tkinter GUI for the nanoject TTL pulse controller."""
from __future__ import annotations

import queue
import time
import tkinter as tk
from tkinter import messagebox, ttk

from .controller import Controller, list_serial_ports

# --- Adjustable defaults ---
DEFAULT_NUM_PULSES = 10
DEFAULT_INTERVAL_MS = 1000
DEFAULT_BAUD = 115200


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Nanoject Controller")
        root.resizable(False, False)

        self.controller: Controller | None = None
        self.running = False
        self.start_time: float | None = None
        self.total_duration_s = 0.0
        self.pulses_total = 0
        self.pulses_emitted = 0

        self._build_ui()
        self._refresh_ports()
        self._poll_events()
        self._tick_clock()

        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        conn = ttk.LabelFrame(self.root, text="Connection")
        conn.grid(row=0, column=0, sticky="ew", **pad)
        ttk.Label(conn, text="Port:").grid(row=0, column=0, sticky="e", **pad)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(
            conn, textvariable=self.port_var, width=28, state="readonly"
        )
        self.port_combo.grid(row=0, column=1, **pad)
        ttk.Button(conn, text="Refresh", command=self._refresh_ports).grid(
            row=0, column=2, **pad
        )
        self.connect_btn = ttk.Button(conn, text="Connect", command=self._toggle_connect)
        self.connect_btn.grid(row=0, column=3, **pad)

        settings = ttk.LabelFrame(self.root, text="Pulse settings")
        settings.grid(row=1, column=0, sticky="ew", **pad)
        ttk.Label(settings, text="Number of pulses:").grid(row=0, column=0, sticky="e", **pad)
        self.npulses_var = tk.StringVar(value=str(DEFAULT_NUM_PULSES))
        ttk.Entry(settings, textvariable=self.npulses_var, width=10).grid(
            row=0, column=1, sticky="w", **pad
        )
        ttk.Label(settings, text="Interval (ms):").grid(row=1, column=0, sticky="e", **pad)
        self.interval_var = tk.StringVar(value=str(DEFAULT_INTERVAL_MS))
        ttk.Entry(settings, textvariable=self.interval_var, width=10).grid(
            row=1, column=1, sticky="w", **pad
        )

        btns = ttk.Frame(self.root)
        btns.grid(row=2, column=0, sticky="ew", **pad)
        self.start_btn = ttk.Button(
            btns, text="Start", command=self._start_or_stop, state="disabled"
        )
        self.start_btn.grid(row=0, column=0, **pad)
        self.test_btn = ttk.Button(btns, text="Test", command=self._test, state="disabled")
        self.test_btn.grid(row=0, column=1, **pad)

        prog = ttk.LabelFrame(self.root, text="Progress")
        prog.grid(row=3, column=0, sticky="ew", **pad)
        self.pulse_label = ttk.Label(prog, text="Pulses: 0 / 0")
        self.pulse_label.grid(row=0, column=0, sticky="w", **pad)
        self.time_label = ttk.Label(prog, text="Time: 0.0 / 0.0 s")
        self.time_label.grid(row=1, column=0, sticky="w", **pad)
        self.progress = ttk.Progressbar(prog, mode="determinate", length=300)
        self.progress.grid(row=2, column=0, sticky="ew", **pad)

        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(self.root, textvariable=self.status_var, foreground="gray").grid(
            row=4, column=0, sticky="w", **pad
        )

    def _refresh_ports(self) -> None:
        ports = list_serial_ports()
        self.port_combo["values"] = ports
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])

    def _toggle_connect(self) -> None:
        if self.controller is None:
            port = self.port_var.get().strip()
            if not port:
                messagebox.showerror("No port", "Select a serial port first.")
                return
            try:
                self.controller = Controller(port, baud=DEFAULT_BAUD)
                self.controller.open()
            except Exception as e:
                self.controller = None
                messagebox.showerror("Connect failed", str(e))
                return
            self.connect_btn.config(text="Disconnect")
            self.start_btn.config(state="normal")
            self.test_btn.config(state="normal")
            self.status_var.set(f"Connected to {port}")
        else:
            self._disconnect()

    def _disconnect(self) -> None:
        if self.controller is not None:
            self.controller.close()
            self.controller = None
        self.connect_btn.config(text="Connect")
        self.start_btn.config(state="disabled", text="Start")
        self.test_btn.config(state="disabled")
        self.running = False
        self.status_var.set("Disconnected")

    def _start_or_stop(self) -> None:
        if self.controller is None:
            return
        if self.running:
            self.controller.stop()
            return
        try:
            n = int(self.npulses_var.get())
            interval = int(self.interval_var.get())
            if n <= 0 or interval <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Bad input",
                "Number of pulses and interval must be positive integers.",
            )
            return
        self.pulses_total = n
        self.pulses_emitted = 0
        # First pulse fires at t=0, last at t=(n-1)*interval.
        self.total_duration_s = (n - 1) * interval / 1000.0
        self.start_time = time.monotonic()
        self.running = True
        self.start_btn.config(text="Stop")
        self.test_btn.config(state="disabled")
        self.progress.config(maximum=n, value=0)
        self.pulse_label.config(text=f"Pulses: 0 / {n}")
        self.status_var.set("Running...")
        self.controller.start_sequence(n, interval)

    def _test(self) -> None:
        if self.controller is None:
            return
        self.controller.test_pulse()
        self.status_var.set("Test pulse sent.")

    def _poll_events(self) -> None:
        if self.controller is not None:
            try:
                while True:
                    ev = self.controller.events.get_nowait()
                    self._handle_event(ev)
            except queue.Empty:
                pass
        self.root.after(50, self._poll_events)

    def _handle_event(self, ev: dict) -> None:
        t = ev["type"]
        if t == "pulse":
            self.pulses_emitted = ev["n"]
            self.progress.config(value=self.pulses_emitted)
            self.pulse_label.config(
                text=f"Pulses: {self.pulses_emitted} / {self.pulses_total}"
            )
        elif t == "done":
            self._finish("Done.")
        elif t == "stopped":
            self._finish("Stopped.")
        elif t == "error":
            self.status_var.set(ev["msg"])
        elif t == "disconnect":
            self.status_var.set("Disconnected (port closed).")
            self._disconnect()
        elif t == "ready":
            self.status_var.set("MCU ready.")

    def _finish(self, msg: str) -> None:
        self.running = False
        self.start_btn.config(text="Start")
        self.test_btn.config(state="normal")
        self.status_var.set(msg)

    def _tick_clock(self) -> None:
        if self.running and self.start_time is not None:
            elapsed = time.monotonic() - self.start_time
            self.time_label.config(
                text=f"Time: {elapsed:.1f} / {self.total_duration_s:.1f} s"
            )
        self.root.after(100, self._tick_clock)

    def _on_close(self) -> None:
        if self.controller is not None:
            try:
                self.controller.stop()
            except Exception:
                pass
            self.controller.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
