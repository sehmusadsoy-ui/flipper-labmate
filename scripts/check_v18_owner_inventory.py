#!/usr/bin/env python3
"""E11.1b read-only inventory of exact pinned Momentum HAL resource callers.

SUCCESS means all currently known caller paths were enumerated, NOT that
they use leases. Unknown paths FAIL CLOSED until reviewed. No USB/flash.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

PIN = "d3f89dfe2ef6b01839201598e9be1590cba80322"
EXPECTED = {
    "FuriHalBusTIM1": {
        "targets/f7/furi_hal/furi_hal_pwm.c",
        "targets/f7/furi_hal/furi_hal_ibutton.c",
        "targets/f7/furi_hal/furi_hal_bus.c",
        "targets/f7/furi_hal/furi_hal_nfc_timer.c",
        "targets/f7/furi_hal/furi_hal_rfid.c",
        "targets/f7/furi_hal/furi_hal_infrared.c",
        "targets/f7/furi_hal/furi_hal_speaker.c",
        "lib/signal_reader/signal_reader.c",
        "applications/drivers/subghz/cc1101_ext/cc1101_ext.c",
    },
    "FuriHalBusTIM2": {
        "lib/pulse_reader/pulse_reader.c",
        "targets/f7/furi_hal/furi_hal_rfid.c",
        "lib/digital_signal/digital_sequence.c",
        "targets/f7/furi_hal/furi_hal_subghz.c",
        "targets/f7/furi_hal/furi_hal_bus.c",
        "targets/f7/furi_hal/furi_hal_infrared.c",
    },
    "furi_hal_gpio_add_int_callback": {
        "targets/f7/furi_hal/furi_hal_gpio.c",
        "targets/f7/furi_hal/furi_hal_nfc_irq.c",
        "applications/debug/accessor/helpers/wiegand.cpp",
        "applications/services/input/input.c",
        "lib/one_wire/one_wire_slave.c",
        "applications/system/js_app/modules/js_gpio.c",
        "targets/f7/furi_hal/furi_hal_serial_control.c",
        "applications/drivers/subghz/cc1101_ext/cc1101_ext.c",
        "applications/system/js_app/modules/js_vgm/ICM42688P/ICM42688P.c",
    },
}

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True,
        stderr=subprocess.STDOUT
    ).strip()

def callers(root: Path, name: str) -> set[str]:
    try:
        output = git(root, "grep", "-l", "-F", name, "--",
                     ":(glob)**/*.c", ":(glob)**/*.cpp")
    except subprocess.CalledProcessError as ex:
        # A completely absent entry is still a mismatch; no silent pass.
        if ex.returncode == 1:
            return set()
        raise
    return set(output.splitlines())

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("momentum_root", type=Path)
    args = parser.parse_args()
    try:
        root = args.momentum_root.resolve(strict=True)
        current = git(root, "rev-parse", "HEAD")
        if current != PIN:
            raise ValueError(f"unexpected firmware SHA {current}")
        mismatches = 0
        for symbol, expected in EXPECTED.items():
            observed = callers(root, symbol)
            unreviewed = sorted(observed - expected)
            missing = sorted(expected - observed)
            print(f"{symbol}: {len(observed)} firmware source callers")
            for item in sorted(observed):
                print(f"  {item}")
            if unreviewed:
                print("UNREVIEWED PATHS:", ", ".join(unreviewed))
                mismatches += 1
            if missing:
                print("MISSING EXPECTED PATHS:", ", ".join(missing))
                mismatches += 1
        if mismatches:
            raise ValueError("HAL caller inventory differs from pinned expectations")
        print("E11.1b SOURCE OWNER INVENTORY PASS — caller paths documented.")
        print("ALL THESE LEGACY CALLERS STILL REQUIRE OWNERSHIP REVIEW/MIGRATION.")
        print("NOT GLOBAL LEASE ENFORCEMENT; NO NEW FAP, NO USB, NO FLASH.")
        return 0
    except (OSError, subprocess.CalledProcessError, ValueError) as ex:
        print(f"E11.1b INVENTORY REFUSED: {ex}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
