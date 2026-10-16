#!/usr/bin/env python3
"""READ-ONLY live LabMate microSD vs historical local backup inventory.

Remote commands: device_info (FlipperStorage startup), storage list, storage md5.
No receive/send, remove, format, mkdir, app launch, install or flash.
Requires locally checked-out pinned Momentum firmware scripts/ directory.
Outputs COUNTS only; never prints private device identifiers or file contents.
Missing/mutated/new files are a BACKUP COVERAGE GAP, never automatically fixed.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys
import time

REMOTE_ROOT = "/ext/apps_data/labmate"
MAX_FILES = 512
MAX_DEPTH = 8
MAX_DIRS = 128
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
FILE = re.compile(r"^\[F\] (.+) ([0-9]+)$")
DIRECTORY = re.compile(r"^\[D\] (.+)$")
MD5 = re.compile(r"^[a-fA-F0-9]{32}$")


class DeadlineRead:
    """Finite response deadline instead of upstream BufferedRead's endless loop."""

    def __init__(self, stream, timeout_seconds: float = 20.0):
        if not 2.0 <= timeout_seconds <= 120.0:
            raise ValueError("out-of-range finite serial read timeout")
        self.stream = stream
        self.buffer = bytearray()
        self.timeout_seconds = timeout_seconds

    def until(self, eol: str = "\n", cut_eol: bool = True) -> bytes:
        marker = eol.encode("ascii")
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            index = self.buffer.find(marker)
            if index >= 0:
                cut = index if cut_eol else index + len(marker)
                part = bytes(self.buffer[:cut])
                del self.buffer[:index + len(marker)]
                return part
            if time.monotonic() >= deadline:
                raise TimeoutError("Flipper CLI did not respond within safe deadline")
            chunk = self.stream.read(max(1, min(4096, self.stream.in_waiting)))
            if chunk:
                self.buffer.extend(chunk)
                if len(self.buffer) > 262144:
                    raise ValueError("Flipper CLI response exceeded bounded buffer")


def safe_name(name: str) -> str:
    if not NAME.fullmatch(name) or name in (".", "..") or ".." in name:
        raise ValueError("unsafe/ambiguous SD member name")
    return name


def parse_listing(raw: bytes | str) -> list[tuple[str, str, int]]:
    """Strictly parse Flipper 'storage list' response; refuse unclear output."""
    if isinstance(raw, bytes):
        raw = raw.decode("ascii", errors="strict")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if lines == ["Empty"]:
        return []
    result = []
    seen = set()
    for line in lines:
        if "Storage error:" in line:
            raise ValueError("Flipper SD storage error while listing")
        f = FILE.fullmatch(line)
        d = DIRECTORY.fullmatch(line)
        if f:
            name = safe_name(f.group(1))
            typ = "file"
            size = int(f.group(2))
        elif d:
            name = safe_name(d.group(1))
            typ = "directory"
            size = 0
        else:
            raise ValueError("unrecognized Flipper storage-list response")
        # FAT names are effectively case-insensitive; collisions are unsafe.
        if name.lower() in seen:
            raise ValueError("duplicate/case-fold collision on Flipper SD")
        seen.add(name.lower())
        result.append((typ, name, size))
    return result


def remote_inventory(storage, *, root: str = REMOTE_ROOT) -> dict[str, tuple[int, str]]:
    if root != REMOTE_ROOT:
        raise ValueError("only the pinned LabMate SD data root is allowed")
    pending = [(root, "", 0)]
    records: dict[str, tuple[int, str]] = {}
    dirs = 0
    while pending:
        path, relative, depth = pending.pop()
        dirs += 1
        if dirs > MAX_DIRS or depth > MAX_DEPTH:
            raise ValueError("overlarge/deep SD directory tree")
        storage.send_and_wait_eol('storage list "' + path + '"\r')
        raw = storage.read.until(storage.CLI_PROMPT)
        for kind, name, size in parse_listing(raw):
            subpath = path + "/" + name
            rel = relative + name
            if kind == "directory":
                pending.append((subpath, rel + "/", depth + 1))
                continue
            if len(records) >= MAX_FILES:
                raise ValueError("too many live LabMate files")
            # This official Flipper method issues 'storage md5' only.
            actual = storage.hash_flipper(subpath).strip()
            if not MD5.fullmatch(actual):
                raise ValueError("bad live Flipper MD5 response")
            rel_key = rel.lower()
            if rel_key in records:
                raise ValueError("duplicate live SD relative file path")
            records[rel_key] = (size, actual.lower())
    if not records:
        raise ValueError("LabMate live SD has no readable files (cannot prove parity)")
    return records


def local_inventory(root: Path) -> dict[str, tuple[int, str]]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("historical local LabMate backup directory missing")
    files = [p for p in root.rglob("*") if p.is_file()]
    if not 1 <= len(files) <= MAX_FILES:
        raise ValueError("historical local backup empty/oversized")
    # A historical copy may have been made from a folder into an extra
    # "labmate" directory; allow that single prefix only.
    all_paths = [p.relative_to(root).parts for p in files]
    strip = bool(all_paths and all(len(parts) >= 2 and
                 parts[0].lower() == "labmate" for parts in all_paths))
    result: dict[str, tuple[int, str]] = {}
    for p in root.rglob("*"):
        if p.is_symlink() or not (p.is_file() or p.is_dir()):
            raise ValueError("unsafe symlink/special historical backup entry")
    for p, parts in zip(files, all_paths):
        if strip:
            parts = parts[1:]
        rel = "/".join(safe_name(name) for name in parts).lower()
        if not rel or rel in result:
            raise ValueError("duplicate/ambiguous local backup path")
        hash_md5 = hashlib.md5()
        with p.open("rb") as input_file:
            while chunk := input_file.read(65536):
                hash_md5.update(chunk)
        result[rel] = (p.stat().st_size, hash_md5.hexdigest())
    return result


def compare_backups(
    live: dict[str, tuple[int, str]],
    backup: dict[str, tuple[int, str]],
) -> dict[str, int | str]:
    if not live or not backup:
        raise ValueError("no meaningful backup parity comparison")
    absent = set(backup) - set(live)
    new = set(live) - set(backup)
    modified = {
        key for key in set(live) & set(backup) if live[key] != backup[key]
    }
    matched = len(set(live) & set(backup)) - len(modified)
    return {
        "historical_backup_files": len(backup),
        "current_device_files": len(live),
        "same_path_same_size_md5": matched,
        "historical_files_now_absent": len(absent),
        "new_device_files_not_in_backup": len(new),
        "changed_files_not_covered_by_backup": len(modified),
        "current_data_backup_parity": (
            "MATCH" if not (absent or new or modified) else "GAP"
        ),
        "screening_method": "FILE_PATH_AND_SIZE_PLUS_MD5_ONLY",
        "individual_file_sha256_verified": "NO",
        "full_microSD_covered": "NO",
        "restoration_rehearsed": "NO",
        "install_authorized": "NO",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True,
                        help="explicit Flipper COM port, e.g. COM7")
    parser.add_argument("--momentum-scripts", type=Path, required=True,
                        help="trusted pinned Momentum firmware scripts/ directory")
    parser.add_argument("--backup-dir", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"COM[1-9][0-9]{0,2}", args.port):
        parser.error("explicit COMn required: no auto guessing or unsafe port")
    if args.momentum_scripts.is_symlink() or not (
        args.momentum_scripts / "flipper" / "storage.py"
    ).is_file():
        parser.error("the expected local Momentum scripts/flipper/storage.py is missing")
    try:
        # Parse/validate local files first, before touching USB.
        backup = local_inventory(args.backup_dir)
        sys.path.insert(0, str(args.momentum_scripts.resolve()))
        import flipper.storage as pinned_storage
        # Never silently import an installed/untrusted different 'flipper'
        # package instead of the exact operator-provided source tree.
        module_path = Path(pinned_storage.__file__).resolve()
        expected_path = (args.momentum_scripts / "flipper" / "storage.py").resolve()
        if module_path != expected_path:
            raise ValueError("wrong Flipper transport module imported")
        # Its start() sends only device_info, then our code only storage list/md5.
        storage = pinned_storage.FlipperStorage(args.port)
        # Replace upstream infinite wait with a finite response deadline,
        # including transport startup and every list/md5 response.
        storage.read = DeadlineRead(storage.port, timeout_seconds=20.0)
        with storage:
            live = remote_inventory(storage)
        result = compare_backups(live, backup)
    except (OSError, ValueError, UnicodeError, ImportError, RuntimeError) as err:
        parser.exit(1, "LABMATE LIVE SD AUDIT REFUSED: " + str(err) + "\n")
    for name, value in result.items():
        print(name + ": " + str(value))
    if result["current_data_backup_parity"] == "GAP":
        print("BACKUP COVERAGE GAP CONFIRMED; DO NOT RESTORE/DELETE/SYNC AUTOMATICALLY")
        return 2
    print("LABMATE LIVE DIRECTORY SIZE+MD5 SCREEN MATCH - NO FLASH")
    print("NOT A FULL SD BACKUP OR RESTORE TEST; SHA256 READBACK NOT VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
