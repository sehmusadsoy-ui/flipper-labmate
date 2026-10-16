#!/usr/bin/env python3
"""Read-only current /ext/Manifest audit for Momentum E11 resource cleanup.

Momentum updater (pinned firmware base d3f89dfe) deletes files named in
the *old on-device resource Manifest* before unpacking the new resources.
An FAP-excluded NEW archive alone does not prove an old installed FAP
would survive cleanup. Inspect LIVE old manifest before approving trial.

Allowed Flipper commands ONLY: device_info (CLI initialization),
storage md5 "/ext/Manifest", storage read_chunks "/ext/Manifest" 2048,
and single-byte 'y' READ handshakes. No SD device write, file creation,
firmware install, restoration, application closing or flash operations.
Only count/boolean summaries are displayed; no other-app paths printed.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from backup_v18_e11_usb_sd_to_pc import _cmd, _line, _read_exact, _md5

MANIFEST = b"/ext/Manifest"
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_ENTRIES = 30000
CHUNK = 2048
FILE_RE = re.compile(rb"F:([0-9a-fA-F]{32}):([0-9]{1,10}):(.+)")
VERSION_RE = re.compile(rb"V:([0-9]{1,4})")
TIMESTAMP_RE = re.compile(rb"T:([0-9]{1,16})")
TARGET_FAP = b"apps/tools/labmate.fap"
TARGET_DATA_PREFIX = b"apps_data/labmate/"
MAX_NAME_BYTES = 700
SAFE_MD5 = re.compile(r"[a-f0-9]{32}")


def path_ok(raw: bytes, *, directory: bool = False) -> bytes:
    """Manifest paths are opaque; no names are opened/printed."""
    path = raw.rstrip(b"/") if directory else raw
    if not path or len(path) > MAX_NAME_BYTES:
        raise ValueError("invalid or overlong resource manifest path")
    if path.startswith((b"/", b"\\")) or b"\\" in path or b":" in path:
        raise ValueError("unsafe absolute/drive/resource path")
    parts = path.split(b"/")
    if (any(part in (b"", b".", b"..") for part in parts) or
            any(c < 32 or c == 127 for c in path)):
        raise ValueError("unsafe resource path component")
    return path.lower()


def parse_old_manifest(data: bytes) -> dict[str, object]:
    """Never silently skip an unexpected resource record."""
    if not 1 <= len(data) <= MAX_MANIFEST_BYTES or b"\x00" in data:
        raise ValueError("old resource Manifest absent, empty or oversized")
    files: set[bytes] = set()
    directories: set[bytes] = set()
    version_seen = False
    timestamp_seen = False
    total = 0
    for raw_line in data.splitlines():
        if not raw_line:
            raise ValueError("empty resource manifest record")
        total += 1
        if total > MAX_ENTRIES:
            raise ValueError("too many old manifest entries")
        f = FILE_RE.fullmatch(raw_line)
        if f is not None:
            if int(f.group(2)) > 0xFFFFFFFF:
                raise ValueError("bad resource file size")
            normalized = path_ok(f.group(3))
            if normalized in files or normalized in directories:
                raise ValueError("duplicate resource manifest path")
            files.add(normalized)
        elif raw_line.startswith(b"D:"):
            normalized = path_ok(raw_line[2:], directory=True)
            if normalized in files or normalized in directories:
                raise ValueError("duplicate resource manifest directory")
            directories.add(normalized)
        elif (v := VERSION_RE.fullmatch(raw_line)) is not None:
            if version_seen or int(v.group(1)) != 0:
                raise ValueError("duplicate/unsupported resource manifest version")
            version_seen = True
        elif TIMESTAMP_RE.fullmatch(raw_line) is not None:
            if timestamp_seen:
                raise ValueError("duplicate resource manifest timestamp")
            timestamp_seen = True
        else:
            raise ValueError("unrecognized old resource Manifest entry")
    if not files or not directories or not version_seen or not timestamp_seen or total < 10:
        raise ValueError("implausible incomplete old firmware resource manifest")
    return {
        "old_manifest_resource_files": len(files),
        "old_manifest_directories": len(directories),
        "old_manifest_metadata_lines": 2,
        "old_cleanup_lists_installed_labmate_fap": "YES" if TARGET_FAP in files else "NO",
        "old_cleanup_labmate_data_files": sum(
            p.startswith(TARGET_DATA_PREFIX) for p in files
        ),
        "old_cleanup_non_labmate_apps_data_files": sum(
            p.startswith(b"apps_data/") and not p.startswith(TARGET_DATA_PREFIX)
            for p in files
        ),
        "old_cleanup_app_fap_files": sum(
            p.startswith(b"apps/") and p.endswith(b".fap") for p in files
        ),
        "old_cleanup_lists_apps_tools_parent": "YES" if b"apps/tools" in directories else "NO",
        "manifest_total_records": total,
        "current_installed_manifest_provenance": "READ_FROM_DEVICE_NOT_AUTHENTICATED",
        "old_resource_cleanup_behavior": "REMOVES_OLD_MANIFEST_FILE_ENTRIES",
        "split_new_bundle_excludes_labmate_fap": "YES_REVIEW_ONLY",
        "split_updater_guarantees_exitfix_survival": "NO",
        "exact_prior_firmware_restore_tested": "NO",
        "trial_write_authorized": "NO",
    }


def read_live_manifest(storage) -> tuple[bytes, str]:
    """Raw binary read with deadline; bounded to one public manifest only."""
    before = _md5(storage, MANIFEST)
    if not SAFE_MD5.fullmatch(before):
        raise ValueError("Flipper manifest MD5 not available")
    _cmd(storage, MANIFEST, b"read_chunks", b" " + str(CHUNK).encode("ascii"))
    header = _line(storage)
    match = re.fullmatch(rb"Size: ([0-9]{1,10})", header)
    if match is None:
        raise ValueError("unrecognized Flipper manifest read header")
    size = int(match.group(1))
    if not 1 <= size <= MAX_MANIFEST_BYTES:
        raise ValueError("live manifest length out of bounds")
    pending = size
    output = bytearray()
    while pending:
        storage.read.until("Ready?" + storage.CLI_EOL)
        storage.port.write(b"y")  # Flipper storage READ transfer handshake only
        data = _read_exact(storage, min(pending, CHUNK))
        output.extend(data)
        pending -= len(data)
    storage.read.until(storage.CLI_PROMPT)
    digest = hashlib.md5(output).hexdigest()
    after = _md5(storage, MANIFEST)
    if digest != before or digest != after:
        raise ValueError("Flipper manifest changed or USB binary transfer mismatched")
    return bytes(output), digest


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", required=True)
    p.add_argument("--momentum-scripts", required=True, type=Path)
    args = p.parse_args()
    if not re.fullmatch(r"COM[1-9][0-9]{0,2}", args.port):
        p.error("explicit COMn port is required")
    scripts_file = args.momentum_scripts / "flipper" / "storage.py"
    if (not scripts_file.is_file() or scripts_file.is_symlink()
            or args.momentum_scripts.is_symlink()):
        p.error("pinned local Momentum transport source required")
    try:
        sys.path.insert(0, str(args.momentum_scripts.resolve()))
        import flipper.storage as pinned_storage
        verify_transport_origin(pinned_storage.__file__, args.momentum_scripts)
        storage = pinned_storage.FlipperStorage(args.port)
        storage.read = DeadlineRead(storage.port, timeout_seconds=30)
        with storage as device:
            blob, digest = read_live_manifest(device)
        result = parse_old_manifest(blob)
    except Exception as error:
        # Pinned transport may raise its own Exception subclass; fail closed.
        # Never print a private filename or raw CLI output.
        reason = str(error) if type(error) is ValueError else type(error).__name__
        p.exit(1, "E11 LIVE MANIFEST AUDIT REFUSED - NO WRITE: " + reason + "\n")
    for name, value in result.items():
        print(f"{name}: {value}")
    print("live_manifest_readback_md5_screen: MATCH")
    print("E11 OLD RESOURCE CLEANUP SCOPE AUDIT PASS - FIRMWARE TRIAL NO-GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
