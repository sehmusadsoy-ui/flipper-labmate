#!/usr/bin/env python3
"""Offline comparison of official MNTM-012 rollback and FULL development updater.

Verifies actual bundled RADIO BYTES and option-byte policy match. This does
not prove that device bootloader, resources or user settings migrate safely.
Never connects a USB device or flashes.
"""
from __future__ import annotations

import argparse
import hashlib
import tarfile
from pathlib import Path, PurePosixPath

OFFICIAL_MNTM012_SHA256 = "1d9e1e600c8680172ff6f6913ca0b12484e7d45adbc72a66552e534784c8c1a7"


def members(path: Path) -> dict[str, bytes]:
    result = {}
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            p = PurePosixPath(member.name)
            if p.is_absolute() or ".." in p.parts:
                raise ValueError("unsafe tar member path")
            if member.isdir():
                continue
            if not member.isfile() or len(p.parts) != 2:
                raise ValueError("unexpected archive entry")
            if p.name not in {"radio.bin", "update.fuf"}:
                continue
            if p.name in result or member.size > 2_500_000:
                raise ValueError("duplicate/oversized radio or manifest")
            stream = archive.extractfile(member)
            if not stream:
                raise ValueError("unreadable updater member")
            result[p.name] = stream.read()
    if set(result) != {"radio.bin", "update.fuf"}:
        raise ValueError("radio and update manifest must exist in both full packages")
    return result


def manifest(data: bytes) -> dict[str, str]:
    fields = {}
    for line in data.decode("utf-8").splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            if k in fields:
                raise ValueError("duplicate update.fuf key")
            fields[k] = v.strip()
    return fields


def check(existing_012: Path, new_full: Path) -> str:
    if hashlib.sha256(existing_012.read_bytes()).hexdigest() != OFFICIAL_MNTM012_SHA256:
        raise ValueError("official old rollback TGZ checksum mismatch")
    old = members(existing_012)
    new = members(new_full)
    if old["radio.bin"] != new["radio.bin"]:
        raise ValueError("new radio binary differs from official installed-release radio")
    a, b = manifest(old["update.fuf"]), manifest(new["update.fuf"])
    for key in ("Target", "Radio", "Radio version", "OB reference", "OB mask", "OB write mask"):
        if key not in a or key not in b or a[key] != b[key]:
            raise ValueError("new updater differs in radio/option-byte policy: " + key)
    if a["Target"] != "7" or a["Radio"] != "radio.bin":
        raise ValueError("unexpected old firmware target/radio manifest")
    return hashlib.sha256(old["radio.bin"]).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("official_mntm012_tgz", type=Path)
    parser.add_argument("new_full_tgz", type=Path)
    args = parser.parse_args()
    try:
        digest = check(args.official_mntm012_tgz, args.new_full_tgz)
    except (OSError, ValueError, tarfile.TarError, UnicodeError) as exc:
        parser.exit(1, "REFUSED: " + str(exc) + "\n")
    print("Official MNTM-012 RADIO BYTES and OPTION-BYTE POLICY match new full updater")
    print("radio SHA256:", digest)
    print("SOURCE/ARCHIVE COMPARISON PASS, NOT A PHYSICAL INSTALL/RESTORE PASS")
