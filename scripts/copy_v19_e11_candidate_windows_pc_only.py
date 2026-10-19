#!/usr/bin/env python3
"""V19 E11: copy verified local WSL candidate into NEW Windows PC folder ONLY.

Runs from WSL Python. Rejects overwrites, symlinks, modified SHA256, or
missing historical backups/snapshot. This file has NO serial/Flipper calls,
device write, firmware updater, app installation, or automatic retry.
If a PC write fails, leaves its separate incomplete folder for inspection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from prepare_v19_e11_pc_only import (
    FAP_SHA, FAP_BYTES, V18_SHA, E11_OLD_SHA, verify_backups
)

PC_FILENAME = "labmate-v1.9DEV-E11-WINDOWS-PC-ONLY.fap"
INCOMPLETE = "INCOMPLETE_DO_NOT_USE_FOR_DEVICE_STAGE.txt"
MARKER = "WINDOWS_PC_ONLY_CANDIDATE_VERIFIED.txt"
MANIFEST = "WINDOWS_PC_ONLY_CANDIDATE_MANIFEST.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_candidate(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size != FAP_BYTES:
        raise ValueError("expected exact real WSL v1.9 candidate file missing/unsafe")
    blob = path.read_bytes()
    if len(blob) != FAP_BYTES or sha(blob) != FAP_SHA:
        raise ValueError("v1.9 candidate SHA256 mismatch / unreadable")
    return blob


def destination_check(root: Path, destination: Path, sources: tuple[Path, ...]) -> None:
    """Require one NEW immediate subfolder under explicitly supplied Windows root."""
    if (not root.is_absolute() or not destination.is_absolute() or
            root.is_symlink() or not root.is_dir() or
            destination.is_symlink() or destination.exists()):
        raise ValueError("Windows PC destination/root not safe or not fresh")
    if (root.resolve() != Path("/mnt/c/Users/sehmu/Documents/LabMate-FAP-PC-Backups").resolve() or
            destination.parent.resolve() != root.resolve() or
            not destination.name.startswith("V19-WINDOWS-PC-CANDIDATE-")):
        raise ValueError("allow only a NEW exact Windows PC backup-root child")
    for original in sources:
        p = original.resolve(strict=True)
        if (p == destination or p in destination.parents or
                destination in p.parents or p == root.resolve()):
            raise ValueError("source/backup overlaps stage output")
    if any(part in (".", "..") for part in destination.parts):
        raise ValueError("unsafe destination path segment")


def copy_pc_only(candidate: Path, root: Path, dest: Path,
                 live_v18: Path, historical_e11: Path, data: Path) -> dict:
    count, total = verify_backups(live_v18, historical_e11, data)
    blob = source_candidate(candidate)
    destination_check(root, dest, (candidate, live_v18, historical_e11, data))
    # mkdir with exist_ok=False prevents silently replacing any PC data.
    dest.mkdir(mode=0o700, exist_ok=False)
    (dest / INCOMPLETE).write_text(
        "PC copy incomplete. No Flipper installation authorized.\n", encoding="utf-8"
    )
    output = dest / PC_FILENAME
    with output.open("xb") as stream:
        stream.write(blob)
        stream.flush()
        os.fsync(stream.fileno())
    if output.stat().st_size != FAP_BYTES or sha(output.read_bytes()) != FAP_SHA:
        raise ValueError("Windows mounted-disk FAP SHA256 readback mismatch")
    manifest = {
        "status": "PC_WINDOWS_REVIEW_COPY_ONLY",
        "candidate_sha256": FAP_SHA,
        "candidate_bytes": FAP_BYTES,
        "filename": PC_FILENAME,
        "prior_active_v18_sha256": V18_SHA,
        "historical_e11_v18dev_sha256": E11_OLD_SHA,
        "labmate_snapshot_files_verified": count,
        "labmate_snapshot_bytes": total,
        "device_write": False,
        "install_authorized": False,
        "firmware_flash": False,
        "rollback_rehearsed": False,
    }
    with (dest / MANIFEST).open("x", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    (dest / MARKER).write_text(
        "Verified Windows PC-only copy. NO Flipper SD/USB/firmware writes.\n"
        "Do NOT run real USB stage, rename, restore or flash absent fresh consent.\n",
        encoding="utf-8"
    )
    # Final cross-check before removing the guard marker, and never cleanup a
    # partial transfer automatically on error.
    if sha(output.read_bytes()) != FAP_SHA or len(list(dest.iterdir())) != 4:
        raise ValueError("unexpected Windows PC candidate output inventory")
    (dest / INCOMPLETE).unlink()
    return {
        "status": "V19 WINDOWS PC-ONLY CANDIDATE COPY PASS",
        "candidate_file": str(output),
        "candidate_bytes": FAP_BYTES,
        "candidate_sha256": FAP_SHA,
        "backup_files_verified": count,
        "backup_bytes_verified": total,
        "device_writes": "NONE",
        "firmware_flash": "NONE",
        "install_authorized": "NO",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--windows-pc-backup-root", type=Path, required=True)
    p.add_argument("--destination", type=Path, required=True)
    p.add_argument("--active-v18-backup", type=Path, required=True)
    p.add_argument("--historical-e11-backup", type=Path, required=True)
    p.add_argument("--data-snapshot", type=Path, required=True)
    args = p.parse_args()
    print("V19 E11 WINDOWS PC-ONLY TRANSFER - NO COM/DEVICE OPERATIONS")
    try:
        report = copy_pc_only(
            args.candidate, args.windows_pc_backup_root, args.destination,
            args.active_v18_backup, args.historical_e11_backup,
            args.data_snapshot
        )
    except Exception as exc:
        reason = str(exc) if type(exc) is ValueError else type(exc).__name__
        print("V19 WINDOWS PC ONLY COPY NO-GO: " + reason, file=sys.stderr)
        print("STOP. Preserve any incomplete PC output folder; no retry/overwrite.", file=sys.stderr)
        return 1
    for key, value in report.items():
        print(key + ": " + str(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
