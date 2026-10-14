#!/usr/bin/env python3
"""Read-only proof that a minimal Momentum .tgz contains the EXACT tested DFU.

This checks package identity and absence of radio/resources/option-byte
updates; it never unpacks files onto disk, connects USB or flashes a device.
The DFU identity alone is not proof that the firmware is safe to run.
"""
from __future__ import annotations

import argparse
import hashlib
import tarfile
from pathlib import Path, PurePosixPath


def check_bundle(package: Path, firmware: Path) -> None:
    if not package.is_file() or not firmware.is_file():
        raise ValueError("bundle and DFU files are required")
    expected = hashlib.sha256(firmware.read_bytes()).digest()
    with tarfile.open(package, "r:gz") as archive:
        members = archive.getmembers()
        roots: set[str] = set()
        files: dict[str, bytes] = {}
        for member in members:
            item = PurePosixPath(member.name)
            if (item.is_absolute() or ".." in item.parts or
                    len(item.parts) not in (1, 2)):
                raise ValueError(f"unsafe bundle entry: {member.name!r}")
            roots.add(item.parts[0])
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(f"unexpected link/device: {member.name!r}")
            if len(item.parts) != 2 or item.name in files:
                raise ValueError(f"unexpected duplicate/top-level file: {member.name!r}")
            if member.size > 2_500_000:
                raise ValueError(f"unexpected large file: {member.name!r}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"unreadable member: {member.name!r}")
            files[item.name] = stream.read()
        if len(roots) != 1 or not next(iter(roots)).startswith("f7-update-"):
            raise ValueError("unexpected firmware updater root directory")
        if set(files) != {"firmware.dfu", "updater.bin", "update.fuf"}:
            raise ValueError(f"not a firmware-only minimal updater: {sorted(files)}")
        if hashlib.sha256(files["firmware.dfu"]).digest() != expected:
            raise ValueError("embedded DFU differs from matching compiled firmware")
        if not files["updater.bin"]:
            raise ValueError("empty updater stage")
        text = files["update.fuf"].decode("utf-8")
        keys: dict[str, str] = {}
        for line in text.splitlines():
            if ": " in line:
                key, value = line.split(": ", 1)
                if key in keys:
                    raise ValueError(f"duplicate update manifest field: {key}")
                keys[key] = value.strip()
        if keys.get("Target") != "7":
            raise ValueError("updater target is not Flipper f7")
        if keys.get("Firmware") != "firmware.dfu":
            raise ValueError("update manifest does not target embedded DFU")
        if keys.get("Loader") != "updater.bin":
            raise ValueError("unexpected updater loader")
        for field in ("Radio", "Resources", "Splashscreen"):
            if keys.get(field):
                raise ValueError(f"unexpected additional firmware modification: {field}")
        if "OB write mask" not in keys:
            raise ValueError("missing option-byte write mask")
        mask = keys["OB write mask"].replace(" ", "")
        if mask and any(ch != "0" for ch in mask):
            raise ValueError("updater requests option-byte writes")
    print("MINIMAL FIRMWARE TGZ/DFU IDENTITY PASS (FILES ONLY; NEVER FLASHED)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tgz", type=Path)
    parser.add_argument("dfu", type=Path)
    args = parser.parse_args()
    try:
        check_bundle(args.tgz, args.dfu)
    except (OSError, tarfile.TarError, UnicodeError, ValueError) as exc:
        parser.exit(1, f"REFUSED: {exc}\n")
