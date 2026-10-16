#!/usr/bin/env python3
"""E11 NON-DESTRUCTIVE microSD scope survey: only named top-level directories.

This is NOT a full-card inventory, copy, recovery check or authorization
to install a firmware updater. Reads only /ext, /ext/apps and
/ext/apps_data via pinned Momentum CLI 'storage list' (and device_info
during handshake). Does not print private path/file names or file data.
No storage md5/read_chunks/send/remove/restore/flash calls.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from audit_v18_e11_live_labmate_sd import (
    DeadlineRead, verify_transport_origin
)

SCOPES = ("/ext", "/ext/apps", "/ext/apps_data")
MAX_RESPONSES = 3
MAX_LIST_ITEMS = 4096
MAX_TOTAL_TOP_FILES = 4096


# Unlike the LabMate BACKUP parser, this survey never follows/opens names.
# Other apps can legitimately use spaces, extra dots and non-ASCII raw bytes.
# Treat filenames as opaque bytes and print aggregate counts ONLY.
OPAQUE_DIR = re.compile(rb"^\[D\] (.+)$")
OPAQUE_FILE = re.compile(rb"^\[F\] (.+) ([0-9]{1,10})b$")
MAX_NAME_BYTES = 255
MAX_SCOPE_BYTES = 262144


def parse_scope_listing(raw: bytes) -> list[tuple[str, bytes, int]]:
    """Strict CLI line grammar; opaque names are NEVER converted to PC paths."""
    if not isinstance(raw, bytes) or len(raw) > MAX_SCOPE_BYTES:
        raise ValueError("unexpected type or size for SD listing")
    lines = [line[1:] if line.startswith(b"\t") else line
             for line in raw.splitlines() if line]
    if lines == [b"Empty"]:
        return []
    result: list[tuple[str, bytes, int]] = []
    seen: set[bytes] = set()
    for line in lines:
        if b"Storage error:" in line:
            raise ValueError("Flipper SD storage error")
        f = OPAQUE_FILE.fullmatch(line)
        d = OPAQUE_DIR.fullmatch(line)
        if f:
            kind, name, size = "file", f.group(1), int(f.group(2))
            if size > 0xFFFFFFFF:
                raise ValueError("invalid Flipper file byte count")
        elif d:
            kind, name, size = "directory", d.group(1), 0
        else:
            raise ValueError("unrecognized top-level Flipper listing")
        # We never use opaque names to construct a device or PC path.
        # Nonetheless refuse malformed path/separator/control and duplicates.
        if (not name or len(name) > MAX_NAME_BYTES or
                name in (b".", b"..") or
                b"/" in name or b"\\" in name or
                any(c < 32 or c == 127 for c in name)):
            raise ValueError("malformed opaque SD top-level name")
        normalized = name.lower()  # ASCII case only; raw bytes kept private
        if normalized in seen:
            raise ValueError("duplicate/case-fold collision in SD listing")
        seen.add(normalized)
        result.append((kind, name, size))
        if len(result) > MAX_LIST_ITEMS:
            raise ValueError("unexpectedly large top-level SD listing")
    return result


def survey(storage) -> dict[str, object]:
    """Bounded, hard-coded read-only listings; never traverse user paths."""
    results: dict[str, list[tuple[str, bytes, int]]] = {}
    for scope in SCOPES:
        storage.send_and_wait_eol('storage list "' + scope + '"\r')
        raw = storage.read.until(storage.CLI_PROMPT)
        entries = parse_scope_listing(raw)
        if len(entries) > MAX_LIST_ITEMS:
            raise ValueError("unexpectedly large top-level SD listing")
        results[scope] = entries

    root = results["/ext"]
    apps = results["/ext/apps"]
    data = results["/ext/apps_data"]
    topdir = {name.lower() for typ, name, _ in root if typ == "directory"}
    if not {b"apps", b"apps_data"} <= topdir:
        raise ValueError("expected /ext/apps and /ext/apps_data folders missing")

    def dirs(scope: str) -> int:
        return sum(1 for kind, _, _ in results[scope] if kind == "directory")

    def files(scope: str) -> int:
        return sum(1 for kind, _, _ in results[scope] if kind == "file")

    if sum(files(scope) for scope in SCOPES) > MAX_TOTAL_TOP_FILES:
        raise ValueError("unexpectedly large top-level file count")

    data_dir_names = {
        name.lower() for typ, name, _ in data if typ == "directory"
    }
    # Those names are compared only locally; not disclosed in output.
    has_labmate = b"labmate" in data_dir_names
    other_data_dirs = len(data_dir_names - {b"labmate"})
    other_data_top_files = files("/ext/apps_data")
    other_app_dirs = dirs("/ext/apps")
    other_app_top_files = files("/ext/apps")

    return {
        "survey_scope": "ONLY /ext, /ext/apps, /ext/apps_data TOP LEVEL",
        "ext_directories": dirs("/ext"),
        "ext_top_level_files": files("/ext"),
        "apps_directories": other_app_dirs,
        "apps_top_level_files": other_app_top_files,
        "apps_data_labmate_folder_present": "YES" if has_labmate else "NO",
        "apps_data_OTHER_directories": other_data_dirs,
        "apps_data_top_level_files": other_data_top_files,
        "non_labmate_content_potentially_outside_existing_snapshot":
            "YES" if other_data_dirs or other_data_top_files
            or other_app_dirs or other_app_top_files else "UNKNOWN",
        "whole_sd_inventory_completed": "NO",
        "whole_sd_snapshot_verified": "NO",
        "non_labmate_sd_files_backed_up": "NO",
        "restore_rehearsed": "NO",
        "E11_firmware_write_authorized": "NO",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--momentum-scripts", required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"COM[1-9][0-9]{0,2}", args.port):
        parser.error("explicit COMn port required")
    expected = args.momentum_scripts / "flipper" / "storage.py"
    if args.momentum_scripts.is_symlink() or expected.is_symlink() or not expected.is_file():
        parser.error("trusted pinned Momentum scripts/flipper/storage.py required")

    try:
        sys.path.insert(0, str(args.momentum_scripts.resolve()))
        import flipper.storage as module
        verify_transport_origin(module.__file__, args.momentum_scripts)
        serial_storage = module.FlipperStorage(args.port)
        serial_storage.read = DeadlineRead(serial_storage.port, timeout_seconds=20)
        with serial_storage as device:
            summary = survey(device)
    except (OSError, ValueError, UnicodeError, ImportError, RuntimeError,
            TimeoutError) as exc:
        parser.exit(1, "E11 EXTERNAL SD SURVEY REFUSED - NO DEVICE WRITE: " + str(exc) + "\n")

    for key, value in summary.items():
        print(key + ": " + str(value))
    print("E11 NON-LABMATE SD TOP-LEVEL SURVEY ONLY - NO FLASH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
