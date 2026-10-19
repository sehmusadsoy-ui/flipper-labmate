#!/usr/bin/env python3
"""v1.9 pretrial checkpoint: read EXACT currently installed v1.8 FAP to a NEW PC folder.

DEVICE READ ONLY: device_info, storage stat, storage md5, storage read_chunks.
NEVER writes, renames, deletes, flashes, resets, runs apps or changes GPIO on
Flipper. A new Windows PC backup is written only after a matching on-device
phase-2B state and a byte-exact readback have been verified twice.
This does not authorize installing any v1.9 candidate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from check_v18_e11_final_fap_prewrite_ro import (
    EXPECTED_SHA as OLD_DEV_SHA, pinned_local_expectation,
)
from check_v18_e11_phase2b_state_readonly import audit
from stage_v18_final_fap_on_device_one_file import local_preflight

ACTIVE_REMOTE = "/ext/apps/Tools/labmate.fap"
EXPECTED_ACTIVE_SHA = "393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61"
EXPECTED_ACTIVE_BYTES = 81528
EXPECTED_OLD_DEV_SHA = "2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0"
FAP_NAME = "installed_LabMate_v18_FINAL_E11_before_v19.fap"
REPORT_NAME = "LIVE_V18_FAP_READBACK_REPORT.json"
MARKER = "READ_ONLY_PC_V18_FAP_BACKUP_VERIFIED.txt"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_destination(destination: Path) -> None:
    if not destination.is_absolute() or destination.exists() or destination.is_symlink():
        raise ValueError("new absolute PC-only backup folder required; no overwrite")
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise ValueError("backup parent must already exist and cannot be a symlink")


def check_local(final_fap: Path, old_backup: Path, old_candidate: Path) -> tuple[dict, dict, str]:
    if final_fap.is_symlink() or not final_fap.is_file():
        raise ValueError("trusted final v1.8 candidate missing")
    if final_fap.stat().st_size != EXPECTED_ACTIVE_BYTES:
        raise ValueError("final v1.8 byte size mismatch")
    if sha256(final_fap.read_bytes()) != EXPECTED_ACTIVE_SHA:
        raise ValueError("final v1.8 SHA256 mismatch")
    if OLD_DEV_SHA != EXPECTED_OLD_DEV_SHA:
        raise ValueError("historical E11 original FAP identity changed")

    # Old candidate + actual readback backup provenance and final v1.8 FAP
    # are all hash-checked BEFORE communicating with the device.
    final_bytes = local_preflight(final_fap, old_backup, old_candidate)
    if sha256(final_bytes) != EXPECTED_ACTIVE_SHA:
        raise ValueError("final candidate preflight mismatch")
    post, js = pinned_local_expectation(old_candidate)
    return post, js, hashlib.md5(final_bytes).hexdigest()


def readback_exact(client, post: dict, js: dict, final_md5: str) -> bytes:
    """Only read data; re-audit all on-device identities after the binary read."""
    first = audit(client, post, js, post["E11_APP"], final_md5)
    if first["state"] != "AFTER_PROMOTION" or first["new_v18_FAP"] != "ACTIVE_MD5_AND_SIZE_PASS":
        raise ValueError("active device is not the verified v1.8 final promotion state")

    raw = client.read_file(ACTIVE_REMOTE)
    if not isinstance(raw, (bytes, bytearray)):
        raise ValueError("Flipper FAP readback was not binary data")
    data = bytes(raw)
    if len(data) != EXPECTED_ACTIVE_BYTES or sha256(data) != EXPECTED_ACTIVE_SHA:
        raise ValueError("live v1.8 FAP byte readback differs from independently pinned candidate")
    if hashlib.md5(data).hexdigest() != final_md5:
        raise ValueError("live v1.8 FAP readback MD5 mismatch")

    second = audit(client, post, js, post["E11_APP"], final_md5)
    if second != first:
        raise ValueError("device FAP or native resource identity changed while reading")
    return data


def write_backup(destination: Path, data: bytes) -> Path:
    check_destination(destination)
    if len(data) != EXPECTED_ACTIVE_BYTES or sha256(data) != EXPECTED_ACTIVE_SHA:
        raise ValueError("refuse unverified PC backup bytes")

    destination.mkdir(mode=0o700)
    incomplete = destination / "INCOMPLETE_DO_NOT_RESTORE.txt"
    incomplete.write_text("Backup not yet verified. Do not deploy or restore.\n", encoding="utf-8")
    fap = destination / FAP_NAME
    with fap.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if fap.stat().st_size != EXPECTED_ACTIVE_BYTES or sha256(fap.read_bytes()) != EXPECTED_ACTIVE_SHA:
        raise ValueError("PC FAP disk readback verification failed")

    report = {
        "scope": "single existing /ext/apps/Tools/labmate.fap read to fresh PC folder",
        "remote_path": ACTIVE_REMOTE,
        "installed_version": "v1.8 FINAL E11",
        "device_state_before_and_after_read": "AFTER_PROMOTION",
        "on_device_fap_bytes": EXPECTED_ACTIVE_BYTES,
        "on_device_fap_sha256": EXPECTED_ACTIVE_SHA,
        "pc_disk_readback_sha256": EXPECTED_ACTIVE_SHA,
        "old_v18dev_fap_preserved": True,
        "firmware_js_eventloop_manifest_md5_screen": "PASS",
        "device_writes": False,
        "firmware_flash": False,
        "v19_installed": False,
        "v19_trial_authorized": False,
    }
    record = destination / REPORT_NAME
    with record.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    (destination / MARKER).write_text(
        "ACTIVE v1.8 FAP: byte-for-byte COM7 readback, pinned SHA256, "
        "before/after live MD5/resource state, PC disk readback PASS. "
        "NO DEVICE WRITES.\n", encoding="utf-8")
    incomplete.unlink()
    return fap


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--momentum-scripts", required=True, type=Path)
    parser.add_argument("--old-candidate", required=True, type=Path)
    parser.add_argument("--saved-old-fap-backup", required=True, type=Path)
    parser.add_argument("--final-v18-fap", required=True, type=Path)
    parser.add_argument("--pc-backup", required=True, type=Path)
    args = parser.parse_args()
    print("V19 PRETRIAL - LIVE FINAL V1.8 FAP TO PC ONLY; NO DEVICE WRITES")
    try:
        if not re.fullmatch(r"COM[1-9][0-9]{0,2}", args.port):
            raise ValueError("exact COM port required")
        check_destination(args.pc_backup)
        post, js, final_md5 = check_local(
            args.final_v18_fap, args.saved_old_fap_backup, args.old_candidate
        )
        origin = args.momentum_scripts
        transport_file = origin / "flipper" / "storage.py"
        if origin.is_symlink() or transport_file.is_symlink() or not transport_file.is_file():
            raise ValueError("previously pinned Momentum CLI transport unavailable")
        sys.path.insert(0, str(origin.resolve()))
        import flipper.storage as transport
        verify_transport_origin(transport.__file__, origin)
        client = transport.FlipperStorage(args.port)
        client.read = DeadlineRead(client.port, timeout_seconds=30.0)
        with client as connected:
            blob = readback_exact(connected, post, js, final_md5)
        saved = write_backup(args.pc_backup, blob)
    except Exception as exc:
        reason = str(exc) if type(exc) is ValueError else type(exc).__name__
        print("V19 PRETRIAL FINAL V1.8 PC BACKUP NO-GO: " + reason, file=sys.stderr)
        print("STOP: do not retry, upload, rename, delete, flash or restore.", file=sys.stderr)
        return 1

    print("V19 PRETRIAL FINAL V1.8 LIVE FAP PC BACKUP PASS")
    print("SAVED_PC_FAP:", saved)
    print("FAP_BYTES:", EXPECTED_ACTIVE_BYTES)
    print("FAP_SHA256:", EXPECTED_ACTIVE_SHA)
    print("E11_NATIVE_RESOURCE_SCREEN: PASS")
    print("FLIPPER_WRITES: NONE; V19_FAP_INSTALL: NOT AUTHORIZED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
