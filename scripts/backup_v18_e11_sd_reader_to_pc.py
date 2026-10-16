#!/usr/bin/env python3
"""E11: ONLY PC-side file-content snapshot of externally mounted Flipper SD.

PRECONDITION: stop device, safely remove the microSD and mount it in a
dedicated PC reader. Reads source files ONLY; writes only to a NEW
separate PC output folder. NO Flipper/COM/USB/updater API or SD writes.

Not a raw image, byte-perfect FAT metadata copy, or restore rehearsal.
No source deletion, formatting, sync, overwrites or automatic restore.
Fail-closed: an interrupted copy retains INCOMPLETE-DO-NOT-RESTORE.txt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys

MAX_FILES = 150_000
MAX_TOTAL_BYTES = 512 * (1024 ** 3)
MAX_FILE_BYTES = 256 * (1024 ** 3)
BLOCK = 1024 * 1024
REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _is_reparse(path: Path) -> bool:
    try:
        st = path.lstat()
    except OSError:
        raise ValueError("unable to inspect filesystem entry") from None
    return path.is_symlink() or bool(getattr(st, "st_file_attributes", 0) & REPARSE_POINT)


def _validate_components(root: Path, relative: Path) -> None:
    if relative.is_absolute() or not relative.parts:
        raise ValueError("unsafe relative SD path")
    if any(part in ("", ".", "..") for part in relative.parts):
        raise ValueError("unsafe relative SD component")
    if "\x00" in str(relative):
        raise ValueError("invalid SD entry name")
    if (root / relative).is_symlink():
        raise ValueError("symbolic links are not allowed in SD source")


def inventory(source: Path) -> tuple[list[str], dict[str, int]]:
    """Every directory/file, including hidden, except no symlink or reparse."""
    if not source.is_dir() or _is_reparse(source):
        raise ValueError("SD source is missing or a redirected filesystem")
    directories: set[str] = set()
    files: dict[str, int] = {}
    seen: set[str] = set()

    def walk(folder: Path) -> None:
        with os.scandir(folder) as entries:
            # Do not follow junctions/reparse links or hide scan failures.
            for entry in entries:
                child = Path(entry.path)
                relative = child.relative_to(source)
                _validate_components(source, relative)
                if _is_reparse(child):
                    raise ValueError("SD source contains a link/reparse point")
                key = relative.as_posix()
                folded = key.casefold()
                if folded in seen:
                    raise ValueError("ambiguous SD path collision")
                seen.add(folded)
                metadata = child.lstat()
                if stat.S_ISDIR(metadata.st_mode):
                    directories.add(key)
                    if len(directories) + len(files) > MAX_FILES:
                        raise ValueError("too many SD entries")
                    walk(child)
                elif stat.S_ISREG(metadata.st_mode):
                    if metadata.st_size < 0 or metadata.st_size > MAX_FILE_BYTES:
                        raise ValueError("invalid/oversized SD file")
                    files[key] = metadata.st_size
                    if len(directories) + len(files) > MAX_FILES:
                        raise ValueError("too many SD entries")
                else:
                    raise ValueError("special SD filesystem entry refused")

    walk(source)
    if not files:
        raise ValueError("SD root has no regular files")
    if sum(files.values()) > MAX_TOTAL_BYTES:
        raise ValueError("SD file contents exceed safe transfer limit")
    # Presence only: application data is verified by the PC filesystem.
    if not (source / "apps").is_dir() or not (source / "apps_data" / "labmate").is_dir():
        raise ValueError("not a recognized Flipper SD root")
    return sorted(directories), files


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as inp:
        while data := inp.read(BLOCK):
            digest.update(data)
    return digest.hexdigest()


def copy_and_verify_sd(source: Path, output: Path) -> dict[str, object]:
    """Source is NEVER opened writable. Destination must be new and distinct."""
    if output.exists() or output.is_symlink():
        raise ValueError("destination already exists, refusing overwrite")
    if not output.parent.is_dir() or _is_reparse(output.parent):
        raise ValueError("destination parent missing/redirected")
    if _is_reparse(source) or not source.is_dir():
        raise ValueError("untrusted SD source root")
    resolved_source = source.resolve(strict=True)
    resolved_output = output.resolve(strict=False)
    if (resolved_source == resolved_output or
            resolved_source in resolved_output.parents or
            resolved_output in resolved_source.parents):
        raise ValueError("source and destination paths overlap")
    dirs, files = inventory(source)
    expected_bytes = sum(files.values())
    if shutil.disk_usage(output.parent).free < expected_bytes + 8 * 1024 * 1024:
        raise ValueError("insufficient separate PC disk space")

    # No PC output is created until the source root, contents and disk
    # capacity are validated.
    output.mkdir()
    incomplete = output / "INCOMPLETE-DO-NOT-RESTORE.txt"
    incomplete.write_text(
        "PC-ONLY PARTIAL BACKUP. NEVER restore, overwrite or delete source.\n",
        encoding="utf-8",
    )
    for name in dirs:
        (output / Path(name)).mkdir(parents=True, exist_ok=False)

    manifest: dict[str, dict[str, object]] = {}
    for name, original_size in sorted(files.items()):
        rel = Path(name)
        source_file = source / rel
        destination_file = output / rel
        # EXCLUSIVE creation prevents overwriting PC copy contents.
        source_hash = hashlib.sha256()
        actual_size = 0
        with source_file.open("rb") as inp, destination_file.open("xb") as out:
            while chunk := inp.read(BLOCK):
                actual_size += len(chunk)
                if actual_size > original_size:
                    raise ValueError("SD source file size changed during copy")
                source_hash.update(chunk)
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
        if actual_size != original_size or destination_file.stat().st_size != original_size:
            raise ValueError("SD source or PC copy size mismatch")
        expected_sha = source_hash.hexdigest()
        if _sha(destination_file) != expected_sha:
            raise ValueError("PC disk copy SHA256 mismatch")
        manifest[name] = {"size": original_size, "sha256": expected_sha}

    # Detect changes during copying, including new/deleted empty folders,
    # new/deleted paths, content changes keeping identical size.
    after_dirs, after_files = inventory(source)
    if dirs != after_dirs or files != after_files:
        raise ValueError("SD source tree changed during snapshot")
    for name, data in manifest.items():
        if _sha(source / Path(name)) != data["sha256"]:
            raise ValueError("SD content changed during snapshot")
        if _sha(output / Path(name)) != data["sha256"]:
            raise ValueError("new PC copy drifted after write")
    report = {
        "scope": "PC-reader mounted Flipper SD filesystem contents",
        "files_copied_and_sha256_verified": len(files),
        "directories_recorded": len(dirs),
        "total_content_bytes": expected_bytes,
        "source_writes": False,
        "restore_rehearsed": False,
        "filesystem_metadata_or_raw_image_verified": False,
        "E11_firmware_install_authorized": False,
        "files": manifest,
        "directories": dirs,
    }
    with (output / "PC_ONLY_SD_SHA256_MANIFEST.json").open("x", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=2, sort_keys=True)
        fp.write("\n")
        fp.flush()
        os.fsync(fp.fileno())
    (output / "READ_ONLY_PC_FILE_SNAPSHOT_VERIFIED.txt").write_text(
        "CONTENT ONLY: every SD source file and PC copy verified by SHA256. "
        "NOT a raw SD/FAT metadata image, install authorization or restore test.\n",
        encoding="utf-8",
    )
    incomplete.unlink()
    return {
        "files_copied_and_sha256_verified": len(files),
        "directories_recorded": len(dirs),
        "total_content_bytes": expected_bytes,
        "source_sd_written": "NO",
        "backup_destination_new_pc_only": "YES",
        "raw_SD_image_or_metadata_proved": "NO",
        "restore_rehearsed": "NO",
        "firmware_flash_authorized": "NO",
    }


def check_windows_drive_args(source: Path, output: Path) -> None:
    """Root of a non-system E:/ removable-looking drive; never C:/ by default."""
    if os.name != "nt":
        raise ValueError("interactive backup CLI requires Windows drive letter mount")
    if not re.fullmatch(r"[A-Za-z]:\\", source.anchor):
        raise ValueError("source must be explicitly selected drive-letter SD root")
    if source.resolve(strict=True) != Path(source.anchor).resolve(strict=True):
        raise ValueError("source must be exact drive ROOT, not subdirectory")
    system = os.environ.get("SystemDrive", "C:").casefold()
    if source.drive.casefold() == system:
        raise ValueError("refusing source on Windows system drive")
    if source.drive.casefold() == output.drive.casefold():
        raise ValueError("PC destination must be on a DIFFERENT drive")
    if not (source / "apps_data" / "labmate").is_dir():
        raise ValueError("source drive does not contain expected Flipper data")
    # User is responsible for verifying removable-media identity in Explorer.
    # Drive-letter match alone NEVER proves a physically removable SD card.


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-drive", required=True, type=Path,
                   help="exact SD card reader root such as E:\\ (never guess)")
    p.add_argument("--pc-output", required=True, type=Path,
                   help="new non-existent folder on a separate PC drive")
    args = p.parse_args()
    try:
        check_windows_drive_args(args.source_drive, args.pc_output)
        result = copy_and_verify_sd(args.source_drive, args.pc_output)
    except (OSError, ValueError, UnicodeError, RuntimeError) as exc:
        # Errors never enumerate private source path names.
        p.exit(1, "E11 SD PC BACKUP NOT ACCEPTED - NO FLASH: " + str(exc) + "\n")
    for k, v in result.items():
        print(k + ": " + str(v))
    print("E11 FULL SD FILE-CONTENT PC BACKUP VERIFIED - NO FLASH / NO RESTORE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
