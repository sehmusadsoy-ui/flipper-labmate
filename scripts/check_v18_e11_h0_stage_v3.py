#!/usr/bin/env python3
"""E11 H0 v3: execute ONE staged read-only native JS test after exact file identity.

No upload, flash, reset, JavaScript source rewrite, GPIO pin-mode change or
user-data modification. Requires full pinned bundle FAP/GPIO/event_loop hashes.
Human must verify PWM STOP, no external wiring, and qFlipper closed.
The test's only pin operation is gpio.get("PA7").read() (lease-aware).
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys

from check_v18_e11_h_js_runtime_ro import local_expected_md5, compare_remote_identity, REMOTE

REMOTE_PROBE = "/ext/apps/Scripts/e11_h0_stage_v3.js"
LOCAL_PROBE = Path(__file__).resolve().parents[1] / "tests/device/e11_h0_stage_v3.js"
PINNED_PROBE_SHA256 = "295312109620552b1669533ec644f4fe9f7d150055d5859883e38ddcd849f190"

STAGES = (
    ("begin", b"E11_H3_BEGIN"),
    ("event_loop", b"E11_H3_EVENT_LOOP_OK"),
    ("gpio", b"E11_H3_GPIO_OK"),
    ("pin", b"E11_H3_PIN_OK"),
    ("read", b"E11_H3_READ_OK"),
)


def prove_local_script() -> str:
    if LOCAL_PROBE.is_symlink() or not LOCAL_PROBE.is_file():
        raise ValueError("v3 source file missing or linked")
    blob = LOCAL_PROBE.read_bytes()
    if not 0 < len(blob) < 4096 or hashlib.sha256(blob).hexdigest() != PINNED_PROBE_SHA256:
        raise ValueError("v3 script SHA256 mismatch")
    return hashlib.md5(blob).hexdigest()


def stage_status(raw: bytes) -> str:
    """Return only names of passed stages and runtime status; no raw CLI data."""
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= 65536:
        raise ValueError("invalid bounded CLI response")
    present = [token in raw for _, token in STAGES]
    flags = {
        "launched": b"Running script " in raw,
        "error": b"---- ERROR ----" in raw,
        "trace": b"Trace:" in raw,
        "done": b"Script done!" in raw,
        "gpio_busy": b"GPIO pin BUSY" in raw,
    }
    pairs = [f"{name}={'YES' if seen else 'NO'}" for (name, _), seen in zip(STAGES, present)]
    pairs.extend(f"{name}={'YES' if flag else 'NO'}" for name,flag in flags.items())
    return "H3_FLAGS " + " ".join(pairs)


def evaluate_output(raw: bytes) -> str:
    status = stage_status(raw)
    flags = [token in raw for _, token in STAGES]
    error = b"---- ERROR ----" in raw
    busy = b"GPIO pin BUSY" in raw
    done = b"Script done!" in raw
    launched = b"Running script " in raw
    trace = b"Trace:" in raw
    # Exact-stage order, no duplicate markers, no future stage if earlier missing.
    if all(flags) and launched and done and not (error or busy or trace):
        indices=[raw.find(token) for _, token in STAGES]
        unique=all(raw.count(token)==1 for _,token in STAGES)
        if indices == sorted(indices) and unique:
            return "E11 H0 v3 FREE PA7 JS READ PASS - " + status
    raise ValueError("H0 v3 staged JS not an unambiguous successful read - " + status)


def run(port: str, scripts: Path, candidate: Path) -> str:
    if not re.fullmatch(r"COM[1-9][0-9]{0,2}", port):
        raise ValueError("explicit COMn required")
    module = scripts / "flipper/storage.py"
    if scripts.is_symlink() or module.is_symlink() or not module.is_file():
        raise ValueError("pinned Momentum transport absent")
    probe_md5 = prove_local_script()
    full = local_expected_md5(candidate)  # SHA256-check FULL bundle and 3 expected paths
    from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin

    sys.path.insert(0, str(scripts.resolve()))
    import flipper.storage as transport
    verify_transport_origin(transport.__file__, scripts)
    device = transport.FlipperStorage(port)
    device.read = DeadlineRead(device.port,timeout_seconds=25)
    with device as client:
        client.send_and_wait_eol("device_info\r")
        identity = client.read.until(client.CLI_PROMPT)
        remote={name:client.hash_flipper(path).strip() for name,path in REMOTE.items()}
        compare_remote_identity(identity,remote,full)
        actual=client.hash_flipper(REMOTE_PROBE).strip().lower()
        if actual != probe_md5:
            raise ValueError("remote v3 JS MD5 mismatch or file missing")
        # Exactly one read-only native JS script, no writes or command retries.
        client.send_and_wait_eol("js "+REMOTE_PROBE+"\r")
        output=client.read.until(client.CLI_PROMPT)
    return evaluate_output(output)


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port",required=True)
    p.add_argument("--momentum-scripts",type=Path,required=True)
    p.add_argument("--candidate",type=Path,required=True)
    args=p.parse_args()
    print("E11 H0 v3: exact JS/FAP/plugin identity + one staged GPIO read; NO FLASH/WRITE.")
    print("Operator prerequisite: PWM STOP, LabMate closed, no GPIO wires, qFlipper closed.")
    try:
        result=run(args.port,args.momentum_scripts,args.candidate)
    except ValueError as exc:
        # Only fixed source-controlled messages and boolean classifications
        print("E11 H0 v3 INCOMPLETE: "+str(exc),file=sys.stderr)
        print("H1/H2 NOT AUTHORIZED. DO NOT RETRY BLINDLY.",file=sys.stderr)
        return 1
    except Exception as exc:
        print("E11 H0 v3 INCOMPLETE: "+type(exc).__name__,file=sys.stderr)
        print("H1/H2 NOT AUTHORIZED. DO NOT RETRY BLINDLY.",file=sys.stderr)
        return 1
    print(result)
    print("Only H0 proves native JS free-state read, not cross-service overlap.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
