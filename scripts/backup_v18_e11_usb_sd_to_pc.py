#!/usr/bin/env python3
"""Optional E11 USB full /ext FILE CONTENT backup; NOT a disk image or restore.

Read-only Flipper commands: device_info, storage list, storage md5,
storage read_chunks and the 'y' chunk READ handshake. File transfers
write only to a NEW PC directory, NEVER back to the Flipper.
The script first inventories the complete /ext tree and refuses unsafe
or unrepresentable paths BEFORE creating any PC output. SOURCE does not
need to be removed from Flipper. Firmware flash is NEVER authorized.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from survey_v18_e11_external_sd_ro import parse_scope_listing

ROOT = b"/ext"
MAX_DEPTH = 14
MAX_DIRS = 4096
MAX_FILES = 30000
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
BUFFER_SIZE = 2048  # small USB batches avoid excessively long transfers
MAX_PATH_BYTES = 768
FILE_TIMEOUT = 60.0
WINDOWS_RESERVED = {"con", "prn", "aux", "nul"} | {
    ("com" + str(n)) for n in range(1, 10)
} | {("lpt" + str(n)) for n in range(1, 10)}
MD5 = re.compile(rb"[a-fA-F0-9]{32}")


def name_for_pc(raw: bytes) -> str:
    """One original CLI name as safe UTF-8 PC segment; never sanitize/rename."""
    try:
        name = raw.decode("utf-8", "strict")
    except UnicodeError:
        raise ValueError("unsupported non-UTF8 SD filename; no full backup claim") from None
    if (not name or len(name) > 160 or
            name in (".", "..") or name.endswith((".", " ")) or
            any(c in '<>:"/\\|?*' or ord(c) < 32 or ord(c) == 127 for c in name) or
            name.split(".")[0].casefold() in WINDOWS_RESERVED):
        raise ValueError("SD name cannot be represented safely on Windows")
    return name


def command_path(raw_components: tuple[bytes, ...]) -> bytes:
    if len(raw_components) > MAX_DEPTH:
        raise ValueError("SD recursion depth exceeded")
    path = ROOT
    for item in raw_components:
        name_for_pc(item)
        path += b"/" + item
    if len(path) > MAX_PATH_BYTES:
        raise ValueError("SD remote command path too long")
    return path


def safe_pc_output(output: Path, protected: tuple[Path, ...]) -> None:
    if output.exists() or output.is_symlink():
        raise ValueError("output must be a fresh empty-name PC folder")
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError("output parent must already exist on PC")
    dest = output.resolve(strict=False)
    for source in protected:
        old = source.resolve(strict=False)
        if dest == old or old in dest.parents or dest in old.parents:
            raise ValueError("output overlaps existing LabMate backup")


def _cmd(storage, path: bytes, opcode: bytes, suffix: bytes = b"") -> None:
    if opcode not in (b"list", b"md5", b"read_chunks"):
        raise ValueError("forbidden remote command")
    if b'"' in path or b"\r" in path or b"\n" in path:
        raise ValueError("unsafe remote CLI name")
    storage.port.write(b"storage " + opcode + b' "' + path + b'"' + suffix + b"\r")
    storage.read.until(storage.CLI_EOL)  # echoed CLI command


def _line(storage) -> bytes:
    return storage.read.until(storage.CLI_EOL)


def _md5(storage, path: bytes) -> str:
    _cmd(storage, path, b"md5")
    answer = _line(storage)
    storage.read.until(storage.CLI_PROMPT)
    if not MD5.fullmatch(answer):
        raise ValueError("remote MD5 unavailable or malformed")
    return answer.lower().decode("ascii")


def _list(storage, components: tuple[bytes, ...]) -> list[tuple[str, bytes, int]]:
    path = command_path(components)
    _cmd(storage, path, b"list")
    payload = storage.read.until(storage.CLI_PROMPT)
    return parse_scope_listing(payload)


def full_inventory(storage) -> tuple[list[tuple[bytes, ...]], dict[tuple[bytes, ...], tuple[int, str]]]:
    """Read-only, snapshot names/sizes/device-MD5 of entire /ext tree."""
    dirs: list[tuple[bytes, ...]] = []
    files: dict[tuple[bytes, ...], tuple[int, str]] = {}
    waiting: list[tuple[bytes, ...]] = [()]
    canonical: set[str] = set()
    total = 0
    while waiting:
        parent = waiting.pop()
        if len(dirs) >= MAX_DIRS:
            raise ValueError("too many SD directories")
        entries = _list(storage, parent)
        dirs.append(parent)
        for kind, raw, size in entries:
            p = parent + (raw,)
            decoded = [name_for_pc(seg) for seg in p]
            key = "/".join(decoded).casefold()
            if key in canonical:
                raise ValueError("unrepresentable case collision between PC paths")
            canonical.add(key)
            command_path(p)
            if kind == "directory":
                if len(dirs) + len(waiting) >= MAX_DIRS:
                    raise ValueError("too many SD directories")
                waiting.append(p)
            else:
                if len(files) >= MAX_FILES or size > MAX_FILE_BYTES:
                    raise ValueError("file count/size exceeds bounded USB backup limits")
                total += size
                if total > MAX_TOTAL_BYTES:
                    raise ValueError("total SD bytes exceed bounded USB backup budget")
                files[p] = (size, _md5(storage, command_path(p)))
    if not files:
        raise ValueError("empty SD file inventory")
    required = {(b"apps",), (b"apps_data",), (b"apps_data", b"labmate")}
    if not required.issubset(set(dirs)):
        raise ValueError("expected Flipper apps/apps_data/labmate folders absent")
    return dirs, files


def _read_exact(storage, needed: int) -> bytes:
    """Deadline-bounded binary read using bytes prefetched by DeadlineRead."""
    if needed < 0 or needed > BUFFER_SIZE:
        raise ValueError("unsafe chunk size")
    buf = bytearray()
    pending = storage.read.buffer
    if pending:
        take = min(needed, len(pending))
        buf.extend(pending[:take])
        del pending[:take]
    deadline = time.monotonic() + FILE_TIMEOUT
    while len(buf) < needed:
        if time.monotonic() >= deadline:
            raise TimeoutError("USB binary chunk transfer timed out")
        received = storage.port.read(needed - len(buf))
        if received:
            buf.extend(received)
    return bytes(buf)


def _read_to_pc(storage, source: tuple[bytes, ...], size: int, output: Path) -> tuple[str, str]:
    """Remote file opened READ-only on Flipper; local output created exclusively."""
    raw_path = command_path(source)
    _cmd(storage, raw_path, b"read_chunks", b" " + str(BUFFER_SIZE).encode("ascii"))
    header = _line(storage)
    m = re.fullmatch(rb"Size: ([0-9]{1,16})", header)
    if not m or int(m.group(1)) != size:
        raise ValueError("USB file size changed or invalid read_chunks header")
    device_md5 = hashlib.md5()
    pc_sha256 = hashlib.sha256()
    with output.open("xb") as handle:
        remaining = size
        while remaining:
            storage.read.until("Ready?" + storage.CLI_EOL)
            storage.port.write(b"y")  # read-only firmware transfer handshake
            data = _read_exact(storage, min(remaining, BUFFER_SIZE))
            handle.write(data)
            device_md5.update(data)
            pc_sha256.update(data)
            remaining -= len(data)
        handle.flush()
        os.fsync(handle.fileno())
    storage.read.until(storage.CLI_PROMPT)
    if output.stat().st_size != size:
        raise ValueError("PC readback file size mismatch")
    sha = hashlib.sha256()
    with output.open("rb") as src:
        while buf := src.read(1024 * 1024):
            sha.update(buf)
    if sha.digest() != pc_sha256.digest():
        raise ValueError("PC file SHA256 verification failed")
    return device_md5.hexdigest(), pc_sha256.hexdigest()


def snapshot(storage, output: Path, protected: tuple[Path, ...]) -> dict[str, object]:
    """All data written to output PC folder; nothing written to the Flipper."""
    safe_pc_output(output, protected)
    directories, files = full_inventory(storage)  # validation BEFORE output
    names = sorted(files, key=lambda p: tuple(name_for_pc(n).casefold() for n in p))
    output.mkdir()
    marker = output / "INCOMPLETE-DO-NOT-RESTORE.txt"
    marker.write_text("Incomplete PC-only USB snapshot. NEVER restore these files.\n", encoding="utf-8")
    for d in sorted(directories, key=len):
        if d:
            (output / Path(*(name_for_pc(n) for n in d))).mkdir(exist_ok=False)
    digest_table: dict[str, dict[str, object]] = {}
    for index, components in enumerate(names):
        remote_size, pre_md5 = files[components]
        relative = Path(*(name_for_pc(n) for n in components))
        destination = output / relative
        actual_md5, sha256 = _read_to_pc(storage, components, remote_size, destination)
        if actual_md5 != pre_md5:
            raise ValueError("USB source MD5 differs from pre-read inventory")
        if _md5(storage, command_path(components)) != pre_md5:
            raise ValueError("device file changed during USB copy")
        digest_table[relative.as_posix()] = {
            "size": remote_size, "source_md5": pre_md5,
            "pc_sha256": sha256,
        }
    # Re-enumerate EVERY directory and recompute EVERY device MD5.
    # No success if a file appeared/deleted/changed during the USB copy.
    second_dirs, second_files = full_inventory(storage)
    if set(second_dirs) != set(directories) or second_files != files:
        raise ValueError("SD content changed during two-pass USB snapshot")
    report = {
        "scope": "entire /ext visible Flipper filesystem FILE CONTENTS",
        "directory_count_including_ext": len(directories),
        "files": digest_table,
        "file_count": len(files),
        "total_bytes": sum(s for s, _ in files.values()),
        "flipper_device_writes": False,
        "whole_sd_raw_image": False,
        "restore_rehearsed": False,
        "firmware_install_authorized": False,
    }
    with (output / "PC_USB_SD_BACKUP_SHA256_MANIFEST.json").open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    (output / "READ_ONLY_USB_FILE_CONTENTS_VERIFIED.txt").write_text(
        "All accessible /ext SD file contents copied and checked using MD5 from device, "
        "PC SHA256, and a second device inventory. NOT a raw image/restore test.\n",
        encoding="utf-8",
    )
    marker.unlink()
    return {
        "usb_snapshot_files_verified": len(files),
        "usb_snapshot_directories": len(directories),
        "usb_snapshot_bytes": sum(s for s, _ in files.values()),
        "flipper_sd_files_modified": "NO",
        "raw_sd_image_proved": "NO",
        "restore_rehearsed": "NO",
        "firmware_install_authorized": "NO",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", required=True)
    p.add_argument("--momentum-scripts", type=Path, required=True)
    p.add_argument("--pc-output", type=Path, required=True)
    p.add_argument("--protected-backup", type=Path, action="append", default=[])
    p.add_argument("--copy", action="store_true",
                   help="explicitly allow creating a NEW PC folder, not device write")
    args = p.parse_args()
    if not re.fullmatch(r"COM[1-9][0-9]{0,2}", args.port):
        p.error("explicit COMn device required")
    module_file = args.momentum_scripts / "flipper" / "storage.py"
    if (not module_file.is_file() or module_file.is_symlink()
            or args.momentum_scripts.is_symlink()):
        p.error("trusted pinned Momentum transport script missing")
    try:
        safe_pc_output(args.pc_output, tuple(args.protected_backup))
        sys.path.insert(0, str(args.momentum_scripts.resolve()))
        import flipper.storage as module
        verify_transport_origin(module.__file__, args.momentum_scripts)
        remote = module.FlipperStorage(args.port)
        remote.read = DeadlineRead(remote.port, timeout_seconds=30)
        with remote as storage:
            if args.copy:
                result = snapshot(storage, args.pc_output, tuple(args.protected_backup))
            else:
                dirs, files = full_inventory(storage)
                result = {
                    "inventory_files": len(files),
                    "inventory_directories": len(dirs),
                    "inventory_bytes": sum(s for s, _ in files.values()),
                    "copy_performed": "NO",
                    "firmware_install_authorized": "NO",
                }
    except (OSError, ValueError, UnicodeError, TimeoutError, RuntimeError, ImportError) as e:
        # Prevent private filenames/paths escaping from nested transport errors.
        note = str(e) if type(e) in (ValueError, TimeoutError) else type(e).__name__
        p.exit(1, "E11 USB SD FILE BACKUP REFUSED - NO DEVICE WRITE: " + note + "\n")
    for k, v in result.items():
        print(f"{k}: {v}")
    print("E11 USB SD " + ("PC FILE SNAPSHOT VERIFIED" if args.copy else "INVENTORY PASS")
          + " - NO FLASH / NO RESTORE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
