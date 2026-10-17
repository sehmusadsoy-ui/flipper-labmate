#!/usr/bin/env python3
"""E11 H: one bounded, read-only native JS GPIO PA7 claim via Flipper USB CLI.

This does NOT upload the JS script, modify firmware, reconfigure GPIO,
run a generator, or change the LabMate app state. The operator must verify
PWM STOP/RUN/STOP on screen and qFlipper must release the COM port.
Only the independently pinned E11 FAP + JS plugin + remote probe are accepted.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys

REMOTE_PROBE = "/ext/apps/Scripts/e11_h_pa7_read_only.js"
LOCAL_PROBE = Path(__file__).resolve().parents[1] / "tests" / "device" / "e11_h_pa7_read_only.js"
EXPECTED_SCRIPT_SHA256 = "2d154f899100767209da1b0504b2954c4aa9766ce409edbe051bf5ea391aa629"
EXPECTED_E11_SHA256 = {
    "labmate.fap": "2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0",
    "js_gpio.module": "fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a",
}
RESOURCE_PATHS = {
    "labmate.fap": "/ext/apps/Tools/labmate.fap",
    "js_gpio.module": "/ext/apps_data/js_app/plugins/js_gpio.fal",
}


def digest(path: Path) -> tuple[str, str]:
    if path.is_symlink() or not path.is_file() or not (0 < path.stat().st_size < 8_000_000):
        raise ValueError("local attestation input missing, linked or incorrectly sized: " + path.name)
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), hashlib.md5(data).hexdigest()


def expected_md5(probe: Path, candidate: Path) -> dict[str, str]:
    if candidate.is_symlink() or not candidate.is_dir():
        raise ValueError("pinned E11 FULL candidate directory unavailable")
    if digest(probe)[0] != EXPECTED_SCRIPT_SHA256:
        raise ValueError("test JS script source SHA256 changed; NO CLI execution")
    actual = {}
    for name, sha in EXPECTED_E11_SHA256.items():
        actual_sha, md5 = digest(candidate / name)
        if actual_sha != sha:
            raise ValueError("pinned E11 source SHA256 mismatch: " + name)
        actual[name] = md5
    actual["probe"] = digest(probe)[1]
    return actual


def evaluate_output(raw: bytes, expectation: str) -> str:
    if expectation not in ("free", "busy") or not isinstance(raw, bytes) or not 1 <= len(raw) <= 65536:
        raise ValueError("invalid JS CLI response or expectation")
    if b"E11_H_PA7_BEGIN" not in raw:
        raise ValueError("test marker missing; JS might not have run")
    success = b"E11_H_PA7_READ_OK " in raw
    busy = b"GPIO pin BUSY" in raw
    error = b"---- ERROR ----" in raw
    if success and busy:
        raise ValueError("contradictory CLI response: do not accept")
    if expectation == "free":
        if success and not busy and not error:
            return "E11 H PA7 JS READ WHEN FREE PASS (UI PWM STOP REQUIRED)"
        raise ValueError("free-state PA7 read did not succeed unambiguously")
    if busy and error and not success:
        return "E11 H PA7 NATIVE JS BUSY DENIAL PASS (UI PWM RUN REQUIRED)"
    raise ValueError("owned-state native JS GPIO claim NOT proven to be refused")


def preflight_device(info: bytes, md5s: dict[str, str], expected: dict[str, str]) -> None:
    if not isinstance(info, bytes) or not 1 <= len(info) < 131072:
        raise ValueError("unexpected device_info reply")
    status = info.decode("utf-8", "strict").lower()
    if "mntm-dev" not in status or "d3f89dfe" not in status:
        raise ValueError("wrong E11 firmware label/base")
    if set(md5s) != set(expected):
        raise ValueError("incomplete remote identity set")
    for key, target in expected.items():
        live = md5s[key].strip().lower()
        if not re.fullmatch(r"[0-9a-f]{32}", live) or live != target:
            raise ValueError("actual installed E11/probe MD5 mismatch: " + key)


def run(port: str, firmware_scripts: Path, candidate: Path, expectation: str) -> str:
    if not re.fullmatch(r"COM[1-9][0-9]{0,2}", port):
        raise ValueError("explicit COMn port required")
    transport_file = firmware_scripts / "flipper" / "storage.py"
    if firmware_scripts.is_symlink() or transport_file.is_symlink() or not transport_file.is_file():
        raise ValueError("pinned Momentum transport scripts directory not found")
    expected = expected_md5(LOCAL_PROBE, candidate)
    from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
    sys.path.insert(0, str(firmware_scripts.resolve()))
    import flipper.storage as flipper_storage
    verify_transport_origin(flipper_storage.__file__, firmware_scripts)
    remote = flipper_storage.FlipperStorage(port)
    remote.read = DeadlineRead(remote.port, timeout_seconds=25.0)
    with remote as device:
        device.send_and_wait_eol("device_info\r")
        info = device.read.until(device.CLI_PROMPT)
        found = {name: device.hash_flipper(path).strip() for name, path in RESOURCE_PATHS.items()}
        found["probe"] = device.hash_flipper(REMOTE_PROBE).strip()
        preflight_device(info, found, expected)
        # This fixed CLI command starts JS in a separate thread.
        # The JS source performs ONLY gpio.get("PA7").read().
        # No storage sends, pin init/writes, firmware changes or reboot.
        device.send_and_wait_eol("js " + REMOTE_PROBE + "\r")
        response = device.read.until(device.CLI_PROMPT)
    return evaluate_output(response, expectation)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--momentum-scripts", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--expect", required=True, choices=("free", "busy"))
    a = parser.parse_args()
    print("E11 H PA7 PROBE: ONLY ONE NATIVE JS gpio.read(); NO FLASH OR PIN MODE CHANGES.")
    print("Operator must verify PWM " + ("RUN" if a.expect == "busy" else "STOP") + " on the device UI.")
    try:
        result = run(a.port, a.momentum_scripts, a.candidate, a.expect)
    except Exception as exc:
        reason = str(exc) if type(exc) is ValueError else type(exc).__name__
        print("E11 H PA7 PROBE INCOMPLETE/FAIL: " + reason, file=sys.stderr)
        print("Do not retry blindly; preserve screen state and report CLI status.", file=sys.stderr)
        return 1
    print(result)
    print("This is only PA7/native JS GPIO read-claim evidence, NOT full firmware ownership acceptance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
