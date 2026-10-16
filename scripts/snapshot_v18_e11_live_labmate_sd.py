#!/usr/bin/env python3
"""LabMate v1.8 E11: snapshot LIVE /ext/apps_data/labmate TO NEW PC FOLDER ONLY.

NO DEVICE WRITES. Device commands: device_info (startup), storage list,
storage md5, storage read_chunks. The 'y' byte during read_chunks is a
read-transfer handshake, never an SD write. No update, sync, restore or install.

Every file is byte-readback to the PC, length and MD5 screened against the
pre-snapshot Flipper listing and SHA256 independently verified after writing.
The LIVE directory is re-inventoried before declaring the snapshot complete.
An incomplete snapshot folder is deliberately RETAINED and labelled INCOMPLETE
on any error; NEVER use it to restore data or overwrite an older backup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys

from audit_v18_e11_live_labmate_sd import (
    DeadlineRead, REMOTE_ROOT, compare_backups, local_inventory,
    remote_inventory, verify_transport_origin,
)

MAX_FILE_BYTES = 10_000_000
MAX_SNAPSHOT_BYTES = 50_000_000
# Windows device path ambiguity (e.g. CON, NUL, COM1) must not create
# special devices under local backup, even though names are valid FAT.
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {
    "COM" + str(n) for n in range(1, 10)
} | {"LPT" + str(n) for n in range(1, 10)}


def check_destination(directory: Path, historical: Path) -> None:
    if directory.exists() or directory.is_symlink():
        raise ValueError("destination already exists; refusing overwrite")
    if not directory.parent.is_dir() or directory.parent.is_symlink():
        raise ValueError("destination parent must be existing real PC folder")
    output = directory.resolve(strict=False)
    old = historical.resolve(strict=True)
    if old == output or old in output.parents or output in old.parents:
        raise ValueError("destination overlaps historical backup folder")


def safe_relative(key: str) -> Path:
    # These are lowercased paths from previously strictly validated
    # remote_inventory; re-validate Windows local destination semantics.
    if not key or key.startswith("/") or "\\" in key or ":" in key:
        raise ValueError("unsafe live SD relative path")
    parts = PurePosixPath(key).parts
    if not parts or len(parts) > 9:
        raise ValueError("unsafe live SD path depth")
    for part in parts:
        if part in ("", ".", "..") or part[-1] in (" ", "."):
            raise ValueError("unsafe Windows path component")
        if part.split(".")[0].upper() in WINDOWS_RESERVED:
            raise ValueError("reserved Windows file name on Flipper")
    return Path(*parts)


def stage_live_snapshot(storage, historical: Path, destination: Path) -> dict[str, object]:
    """Writes PC files only. Caller handles opening/closing Flipper serial."""
    historic = local_inventory(historical)
    check_destination(destination, historical)
    initial = remote_inventory(storage)
    total_bytes = sum(size for size, _ in initial.values())
    if any(size < 0 or size > MAX_FILE_BYTES for size, _ in initial.values()):
        raise ValueError("unsafe live LabMate file size")
    if total_bytes > MAX_SNAPSHOT_BYTES:
        raise ValueError("unsafe total live LabMate data size")
    for key in initial:
        safe_relative(key)
    # All validation above precedes ANY LOCAL output creation.
    destination.mkdir(mode=0o700)
    incomplete = destination / "INCOMPLETE-DO-NOT-RESTORE.txt"
    incomplete.write_text(
        "INCOMPLETE / NOT VERIFIED. Do not restore, overwrite or delete source.\n",
        encoding="utf-8",
    )
    sha256: dict[str, str] = {}
    for key, (size, expected_md5) in sorted(initial.items()):
        # Flipper read_file sends ONLY storage read_chunks/handshake.
        data = storage.read_file(REMOTE_ROOT + "/" + key)
        if len(data) != size:
            raise ValueError("live file size changed while reading")
        if hashlib.md5(data).hexdigest() != expected_md5:
            raise ValueError("live file MD5 changed / incomplete readback")
        desired = destination / safe_relative(key)
        desired.parent.mkdir(parents=True, exist_ok=True)
        if desired.exists() or desired.is_symlink():
            raise ValueError("would overwrite existing local snapshot file")
        checksum = hashlib.sha256(data).hexdigest()
        with desired.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if desired.stat().st_size != size:
            raise ValueError("new PC snapshot disk size mismatch")
        if hashlib.sha256(desired.read_bytes()).hexdigest() != checksum:
            raise ValueError("new PC snapshot disk SHA256 mismatch")
        sha256[key] = checksum
    # Refuse claiming a complete snapshot if live data changed while copied.
    if remote_inventory(storage) != initial:
        raise ValueError("live LabMate data changed during snapshot; preserve INCOMPLETE")
    comparison = compare_backups(initial, historic)
    manifest = {
        "snapshot_scope": "ONLY /ext/apps_data/labmate",
        "snapshot_complete": True,
        "device_write": False,
        "historical_backup_modified": False,
        "full_microSD_backup": False,
        "restoration_rehearsed": False,
        "install_authorized": False,
        "files": {
            key: {"size_bytes": initial[key][0],
                  "md5_device_screen": initial[key][1],
                  "sha256_of_pc_readback": sha256[key]}
            for key in sorted(initial)
        },
        "historical_comparison": comparison,
    }
    report = destination / "PC_SNAPSHOT_MANIFEST.json"
    with report.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    # Explicit final marker only after full contents + manifest complete.
    (destination / "READ_ONLY_SNAPSHOT_VERIFIED.txt").write_text(
        "PC copy of live LabMate directory verified with sizes, remote "
        "MD5 screens and PC SHA256. NOT whole SD or restore rehearsal. "
        "Do not flash until remaining gates accepted.\n",
        encoding="utf-8",
    )
    incomplete.unlink()
    return {
        "snapshot_files_verified": len(initial),
        "snapshot_file_bytes": total_bytes,
        "new_device_files_preserved": comparison["new_device_files_not_in_backup"],
        "changed_device_files_preserved": comparison["changed_files_not_covered_by_backup"],
        "historical_files_not_on_device": comparison["historical_files_now_absent"],
        "old_backup_preserved": "YES",
        "flipper_files_modified": "NO",
        "snapshot_full_microSD": "NO",
        "restore_rehearsed": "NO",
        "firmware_flash_authorized": "NO",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", required=True)
    p.add_argument("--momentum-scripts", required=True, type=Path)
    p.add_argument("--historical-backup", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path,
                   help="brand-new PC-only snapshot directory")
    args = p.parse_args()
    if not re.fullmatch(r"COM[1-9][0-9]{0,2}", args.port):
        p.error("explicit COMn required")
    if args.momentum_scripts.is_symlink() or not (
        args.momentum_scripts / "flipper" / "storage.py"
    ).is_file():
        p.error("trusted Momentum storage.py transport missing")
    try:
        # Fail before opening the port if a destination could overwrite old data.
        check_destination(args.output, args.historical_backup)
        sys.path.insert(0, str(args.momentum_scripts.resolve()))
        import flipper.storage as pinned_storage
        verify_transport_origin(pinned_storage.__file__, args.momentum_scripts)
        serial_storage = pinned_storage.FlipperStorage(args.port)
        serial_storage.read = DeadlineRead(serial_storage.port, timeout_seconds=20)
        with serial_storage as remote:
            result = stage_live_snapshot(
                remote, args.historical_backup, args.output
            )
    except (OSError, ValueError, UnicodeError, RuntimeError, ImportError,
            TimeoutError) as err:
        p.exit(1, "E11 PC SNAPSHOT NOT ACCEPTED; NO DEVICE WRITES: " + str(err) + "\n")
    for key, value in result.items():
        print(key + ": " + str(value))
    print("LIVE LABMATE PC READBACK SNAPSHOT VERIFIED - NO FLASH / NO RESTORE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
