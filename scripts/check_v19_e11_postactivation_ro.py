#!/usr/bin/env python3
"""Independent strictly READ-ONLY v1.9 E11 post-ACTIVATION COM7 classifier.

After separately approved TWO device renames only. Does not invoke an
activation, stage writer or rollback. Exact 5 fixed paths:
  v1.9 active, final v1.8 in dedicated backup, historical E11 backup,
  old v1.9 staging ABSENT, failure-retention backup ABSENT.
Two complete SHA256 FAP readbacks each of active v1.9 + final v1.8 backup
are mandatory, with native E11 resource label and plugin manifest MD5 gates.
The internal installed firmware binary ABI remains UNATTESTED.
NEVER run this against STAGED v1.8-active state; use poststage reader there.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from backup_v19_active_v18_fap_ro import check_local
from check_v18_e11_phase2b_state_readonly import ABSENT
from check_v18_e11_postupdate_readonly import EXPECTED_BASE, EXPECTED_FIRMWARE_LABEL
from check_v18_e11_h_js_runtime_ro import REMOTE as JS_REMOTE
from check_v19_e11_staged_device_ro import verified_candidate
from prepare_v19_e11_pc_only import verify_backups
from simulate_v19_e11_fap_swap_offline import (
    ACTIVE, NEW, CURRENT_BACKUP, LEGACY_BACKUP, FAILED_V19_BACKUP,
    V18_SIZE, V18_SHA, LEGACY_SIZE, LEGACY_SHA, V19_SIZE, V19_SHA
)

STATUS_PATHS = frozenset((ACTIVE, NEW, CURRENT_BACKUP, LEGACY_BACKUP, FAILED_V19_BACKUP))
ALLOWED_SIZES = frozenset((V18_SIZE, LEGACY_SIZE, V19_SIZE))
HEX = re.compile(r"[a-f0-9]{32}\Z")


def load_pin(path: Path, size: int, sha: str) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
        raise ValueError("missing PC backup or unexpected size")
    b = path.read_bytes()
    if len(b) != size or hashlib.sha256(b).hexdigest() != sha:
        raise ValueError("PC backup exact SHA256 mismatch")
    return b


def stat(client, path: str) -> bytes:
    if path not in STATUS_PATHS:
        raise ValueError("unexpected post-activation stat path")
    if client.CLI_EOL != "\r\n" or client.CLI_PROMPT != ">: ":
        raise ValueError("unexpected device CLI framing")
    cmd = f'storage stat "{path}"'
    if client.send_and_wait_eol(cmd + "\r") != cmd.encode("ascii"):
        raise ValueError("post-activation stat echo mismatch")
    line = client.read.until(client.CLI_EOL)
    tail = client.read.until(client.CLI_PROMPT)
    acceptable = {ABSENT} | {
        f"File, size: {n}b".encode("ascii") for n in ALLOWED_SIZES
    }
    if tail != b"\r\n" or line not in acceptable:
        raise ValueError("ambiguous post-activation status")
    return line


def exactly(client, path: str, data: bytes) -> None:
    if path not in STATUS_PATHS:
        raise ValueError("unapproved file readback")
    if stat(client, path) != f"File, size: {len(data)}b".encode("ascii"):
        raise ValueError("FAP exact size/status mismatch: " + path)
    md5 = client.hash_flipper(path)
    if not isinstance(md5, str) or HEX.fullmatch(md5.strip().lower()) is None:
        raise ValueError("unrecognized on-device file MD5")
    if md5.strip().lower() != hashlib.md5(data).hexdigest():
        raise ValueError("on-device FAP MD5 differs from PC source")
    read = client.read_file(path)
    if not isinstance(read, (bytes, bytearray)) or bytes(read) != data:
        raise ValueError("complete on-device binary FAP readback mismatch")
    if hashlib.sha256(bytes(read)).hexdigest() != hashlib.sha256(data).hexdigest():
        raise ValueError("full SHA256 drift")
    if client.hash_flipper(path).strip().lower() != md5.strip().lower():
        raise ValueError("FAP changed during readback")


def identity(client, post: dict, js: dict) -> None:
    if client.send_and_wait_eol("device_info\r") != b"device_info":
        raise ValueError("unrecognized device_info echo")
    data = client.read.until(client.CLI_PROMPT)
    if not isinstance(data, bytes) or not 1 <= len(data) <= 131072:
        raise ValueError("invalid native firmware identity")
    value = data.decode("utf-8", errors="strict").lower()
    if EXPECTED_FIRMWARE_LABEL not in value or EXPECTED_BASE not in value:
        raise ValueError("installed E11 firmware label/base drift")
    for name in ("js_gpio.module", "event_loop"):
        path = JS_REMOTE[name]
        digest = client.hash_flipper(path)
        if not isinstance(digest, str) or digest.strip().lower() != js[name].lower():
            raise ValueError("E11 plugin MD5 mismatch")
    if client.hash_flipper("/ext/Manifest").strip().lower() != post["E11_NEW_MANIFEST"].lower():
        raise ValueError("E11 resource manifest MD5 mismatch")


def classify(client, v19: bytes, v18: bytes, legacy: bytes, post: dict, js: dict) -> dict:
    if ((len(v19), hashlib.sha256(v19).hexdigest()) != (V19_SIZE, V19_SHA) or
        (len(v18), hashlib.sha256(v18).hexdigest()) != (V18_SIZE, V18_SHA) or
        (len(legacy), hashlib.sha256(legacy).hexdigest()) != (LEGACY_SIZE, LEGACY_SHA)):
        raise ValueError("invalid pinned PC FAP inputs")
    for _ in range(2):
        identity(client, post, js)
        exactly(client, ACTIVE, v19)
        exactly(client, CURRENT_BACKUP, v18)
        exactly(client, LEGACY_BACKUP, legacy)
        for path in (NEW, FAILED_V19_BACKUP):
            if stat(client, path) != ABSENT:
                raise ValueError("postactivation forbidden sidecar/backup occupied")
    identity(client, post, js)
    for path in (NEW, FAILED_V19_BACKUP):
        if stat(client, path) != ABSENT:
            raise ValueError("postactivation reserved filename drift")
    return {
        "v19_active": "CONFIRMED_BY_TWO_FULL_SHA256_READBACKS",
        "active_v19_sha256": V19_SHA,
        "final_v18_device_backup": "PRESERVED_TWICE_READBACK",
        "historical_e11_backup": "UNCHANGED_TWICE_READBACK",
        "staging_path": "ABSENT",
        "failed_v19_backup": "ABSENT",
        "native_E11_resources": "PINNED_LABEL_AND_JS_MANIFEST_MD5",
        "installed_firmware_binary_abi": "NOT_ATTESTED",
        "gui_boot": "NOT_TESTED",
        "device_writes": "ZERO",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--momentum-scripts", required=True, type=Path)
    parser.add_argument("--old-candidate", required=True, type=Path)
    parser.add_argument("--saved-old-fap-backup", required=True, type=Path)
    parser.add_argument("--final-v18-fap", required=True, type=Path)
    parser.add_argument("--active-v18-backup", required=True, type=Path)
    parser.add_argument("--data-snapshot", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    print("V19 E11 INDEPENDENT POST-ACTIVATION DEVICE CHECK - STRICT READ ONLY")
    try:
        if args.port != "COM7":
            raise ValueError("unexpected serial port")
        n, size = verify_backups(
            args.active_v18_backup, args.saved_old_fap_backup, args.data_snapshot
        )
        if (n, size) != (12, 2128):
            raise ValueError("LabMate PC backup snapshot changed")
        v19 = verified_candidate(args.candidate)
        v18 = load_pin(args.active_v18_backup /
             "installed_LabMate_v18_FINAL_E11_before_v19.fap", V18_SIZE, V18_SHA)
        legacy = load_pin(args.saved_old_fap_backup /
             "installed_E11_v18DEV_before_final_label.fap", LEGACY_SIZE, LEGACY_SHA)
        post, js, _ = check_local(
            args.final_v18_fap, args.saved_old_fap_backup, args.old_candidate
        )
        source = args.momentum_scripts
        sdkpath = source / "flipper" / "storage.py"
        if source.is_symlink() or sdkpath.is_symlink() or not sdkpath.is_file():
            raise ValueError("native serial transport missing")
        sys.path.insert(0, str(source.resolve()))
        import flipper.storage as sdk
        verify_transport_origin(sdk.__file__, source)
        port = sdk.FlipperStorage(args.port)
        port.read = DeadlineRead(port.port, timeout_seconds=40)
        with port as connected:
            report = classify(connected, v19, v18, legacy, post, js)
    except Exception as exc:
        why = str(exc) if type(exc) is ValueError else type(exc).__name__
        print("V19 E11 INDEPENDENT POSTACTIVATION READ-ONLY NO-GO: " + why, file=sys.stderr)
        print("STOP: NO RETRY/RENAME/RESTORE/FLASH. Preserve exactly observed state.", file=sys.stderr)
        return 1
    for name, value in report.items():
        print(name + ": " + value)
    print("V19 E11 INDEPENDENT REAL POSTACTIVATION STATE PASS")
    print("Do not claim GUI/firmware ABI PASS until tested separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
