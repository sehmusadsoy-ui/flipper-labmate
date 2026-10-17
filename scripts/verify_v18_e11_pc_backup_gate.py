#!/usr/bin/env python3
"""Verify BOTH independently preserved LabMate PC backup states before E11 trial.

Offline only: never opens a COM port, contacts Flipper, restores, or flashes.
The count and byte expectations are specific to the operator's 2026-10-17
read-only snapshot; a different live state requires a fresh owner review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

HISTORICAL_COUNT = 14
CURRENT_COUNT = 10
CURRENT_BYTES = 1791
SNAPSHOT_SCOPE = "ONLY /ext/apps_data/labmate"
MANIFEST = "PC_SNAPSHOT_MANIFEST.json"
VERIFIED = "READ_ONLY_SNAPSHOT_VERIFIED.txt"
INCOMPLETE = "INCOMPLETE-DO-NOT-RESTORE.txt"
HEX32 = re.compile(r"[0-9a-fA-F]{32}\Z")
HEX64 = re.compile(r"[0-9a-fA-F]{64}\Z")
COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def members(folder: Path) -> dict[str, Path]:
    require(folder.is_dir() and not folder.is_symlink(), "PC backup folder unavailable or link")
    found: dict[str, Path] = {}
    for entry in folder.rglob("*"):
        require(not entry.is_symlink(), "backup contains symlink")
        require(entry.is_file() or entry.is_dir(), "backup has unsupported file type")
        if entry.is_dir():
            continue
        parts = entry.relative_to(folder).parts
        for part in parts:
            require(bool(COMPONENT.fullmatch(part)) and part not in (".", ".."),
                    "unsafe PC backup relative path")
        key = "/".join(parts).lower()
        require(key not in found, "case-colliding files in PC backup")
        found[key] = entry
    return found


def safe_snapshot_key(key: str) -> str:
    require(isinstance(key, str) and bool(key) and not key.startswith("/"),
            "invalid snapshot file key")
    parts = key.split("/")
    require(len(parts) <= 9 and all(
        p not in (".", "..") and COMPONENT.fullmatch(p) and not p.endswith(".")
        for p in parts
    ), "unsafe snapshot file key")
    return "/".join(parts).lower()


def verify(historical: Path, current: Path) -> dict[str, int]:
    old_root = historical.resolve(strict=True)
    new_root = current.resolve(strict=True)
    require(old_root != new_root and old_root not in new_root.parents
            and new_root not in old_root.parents, "backup folders overlap")
    require(not historical.is_symlink() and not current.is_symlink(),
            "backup folder symlink not allowed")
    old_files = members(historical)
    # Historical copy may be nested under a 'labmate' folder.
    require(len(old_files) == HISTORICAL_COUNT, "historical 14-file backup count mismatch")
    require(all(p.stat().st_size > 0 for p in old_files.values()),
            "empty historical backup file")
    new_files = members(current)
    require(INCOMPLETE.lower() not in new_files, "incomplete current snapshot")
    require(VERIFIED.lower() in new_files and MANIFEST.lower() in new_files,
            "verified snapshot marker or manifest missing")
    report = json.loads(new_files[MANIFEST.lower()].read_text(encoding="utf-8"))
    require(isinstance(report, dict), "snapshot manifest must be object")
    require(report.get("snapshot_scope") == SNAPSHOT_SCOPE and
            report.get("snapshot_complete") is True and
            report.get("device_write") is False and
            report.get("historical_backup_modified") is False and
            report.get("install_authorized") is False and
            report.get("full_microSD_backup") is False and
            report.get("restoration_rehearsed") is False,
            "snapshot provenance/scope is not accepted")
    listed = report.get("files")
    require(isinstance(listed, dict) and len(listed) == CURRENT_COUNT,
            "current 10-file snapshot manifest count mismatch")
    expected = {}
    byte_total = 0
    for raw_key, meta in listed.items():
        key = safe_snapshot_key(raw_key)
        require(key == raw_key and key not in expected, "noncanonical snapshot file key")
        require(isinstance(meta, dict), "snapshot file metadata missing")
        size, md5, sha = (meta.get("size_bytes"), meta.get("md5_device_screen"),
                          meta.get("sha256_of_pc_readback"))
        require(type(size) is int and 0 <= size <= 10_000_000 and
                isinstance(md5, str) and HEX32.fullmatch(md5) and
                isinstance(sha, str) and HEX64.fullmatch(sha),
                "snapshot file metadata invalid")
        require(key in new_files, "snapshot file missing from PC")
        data = new_files[key].read_bytes()
        require(len(data) == size and hashlib.md5(data).hexdigest() == md5.lower()
                and hashlib.sha256(data).hexdigest() == sha.lower(),
                "PC snapshot file checksum/size mismatch")
        byte_total += size
        expected[key] = True
    require(byte_total == CURRENT_BYTES, "current 1791-byte snapshot total mismatch")
    require(set(new_files) == set(expected) | {MANIFEST.lower(), VERIFIED.lower()},
            "unlisted extra file in current PC backup")
    require(new_files[VERIFIED.lower()].stat().st_size > 0,
            "verified snapshot marker empty")
    return {"historical_files": len(old_files), "current_files": len(expected),
            "current_bytes": byte_total}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--historical", type=Path, required=True)
    p.add_argument("--current", type=Path, required=True)
    args = p.parse_args()
    try:
        result = verify(args.historical, args.current)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as err:
        print("E11 PC BACKUP GATE REFUSED: " + str(err), file=sys.stderr)
        return 1
    print("E11 TWO-STATE PC BACKUP GATE PASS - OFFLINE ONLY")
    print("historical_files: {historical_files}; current_files: {current_files}; current_bytes: {current_bytes}".format(**result))
    print("NO RESTORE TEST, NO LIVE DEVICE CHECK, NO FLASH AUTHORIZATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
