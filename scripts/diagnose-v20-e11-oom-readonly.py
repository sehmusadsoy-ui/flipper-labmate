#!/usr/bin/env python3
"""Read-only Momentum E11 CLI heap snapshot for v2.0 LabMate P0-01.

This utility only opens an already-exposed USB CDC CLI and sends 'free'.
No FAP launches/installation, no firmware commands, no SD or GPIO writes.
Use before LabMate launch, particularly after long idle and after reboot.
"""
from __future__ import annotations

import argparse
import re
import sys
import time

HEAP_KEYS = (
    "Free heap size",
    "Total heap size",
    "Minimum heap size",
    "Maximum heap block",
    "Pool free",
    "Maximum pool block",
)
_RE = re.compile(
    r"^(Free heap size|Total heap size|Minimum heap size|Maximum heap block|"
    r"Pool free|Maximum pool block):\s*(\d+)\s*$",
    re.MULTILINE,
)


def parse_free(text: str) -> dict[str, int]:
    """Parse only the six read-only values emitted by the pinned E11 CLI."""
    data = {key: int(value) for key, value in _RE.findall(text.replace("\r", ""))}
    return data if all(key in data for key in HEAP_KEYS) else {}


def choose_port(ports: list[object], requested: str | None) -> str:
    """Fail closed on missing or ambiguous ports; do not guess USB devices."""
    if requested:
        if not any(str(p.device).upper() == requested.upper() for p in ports):
            raise ValueError("Specified COM port is not connected")
        return requested
    matching = [
        p.device
        for p in ports
        if "flipper" in f"{p.description} {p.manufacturer} {p.product}".lower()
        or (p.vid == 0x0483 and p.pid == 0x5740)
    ]
    if len(matching) == 1:
        return matching[0]
    all_ports = ", ".join(f"{p.device} ({p.description})" for p in ports) or "(none)"
    raise ValueError(
        "Could not select a unique Flipper USB CLI. Connected ports: "
        + all_ports
        + ". Use --port COMx for the verified Flipper port."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Verified Flipper USB CLI, e.g. COM7")
    parser.add_argument(
        "--phase",
        choices=("fresh", "after-idle", "after-exit"),
        default="after-idle",
        help="Printed snapshot label; does not change device state",
    )
    ns = parser.parse_args(argv)

    try:
        import serial
        from serial.tools import list_ports
    except ImportError:
        print("NO-GO: Windows pyserial missing. Install with py -3 -m pip install pyserial.", file=sys.stderr)
        return 2

    ports = list(list_ports.comports())
    try:
        port = choose_port(ports, ns.port)
    except ValueError as exc:
        print(f"NO-GO: {exc}", file=sys.stderr)
        return 2

    try:
        with serial.Serial(port, 115200, timeout=0.2, write_timeout=1) as cli:
            # The only device command sent below is "free" (read-only).
            # Avoid resetting DTR/RTS, flashing, storage commands or logging
            # subscriptions. The CLI itself is opened by the user normally.
            cli.reset_input_buffer()
            cli.write(b"\rfree\r")
            cli.flush()
            end = time.monotonic() + 5.0
            result = bytearray()
            while time.monotonic() < end and len(result) < 8192:
                block = cli.read(512)
                if block:
                    result.extend(block)
                    parsed = parse_free(result.decode("utf-8", "replace"))
                    if parsed:
                        break
    except (serial.SerialException, OSError) as exc:
        print(f"NO-GO: cannot open/read {port} (close qFlipper first): {exc}", file=sys.stderr)
        return 2

    measured = parse_free(result.decode("utf-8", "replace"))
    if not measured:
        print("NO-GO: no complete E11 'free' response; do not infer RAM. Raw CLI:")
        print(result.decode("utf-8", "replace")[-2000:])
        return 3

    print(f"LABMATE E11 MEMORY SNAPSHOT: {ns.phase} | port={port}")
    for field in HEAP_KEYS:
        print(f"{field}: {measured[field]}")
    print(
        "Contiguous/total free ratio: "
        f"{measured['Maximum heap block'] / max(1, measured['Free heap size']):.3f}"
    )
    print("READ ONLY: no app launch, FAP/firmware/SD/GPIO write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
