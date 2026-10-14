#!/usr/bin/env python3
"""Offline audit of an uninstalled, fully paired Momentum updater TGZ.

This validates archive structure and identity; it cannot prove the safety of
writing firmware/radio/option bytes to a physical Flipper. No USB operations.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import tarfile
from pathlib import Path, PurePosixPath

_ALLOWED = {
    "firmware.dfu", "updater.bin", "update.fuf",
    "radio.bin", "resources.tgz", "splash.bin", "firstboot.bin",
}
_REQUIRED = {"firmware.dfu", "updater.bin", "update.fuf", "radio.bin", "resources.tgz"}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def audit(tgz: Path, firmware: Path, radio: Path, max_total: int = 90_000_000):
    if not tgz.is_file() or not firmware.is_file() or not radio.is_file():
        raise ValueError("full TGZ, exact compiled DFU and pinned radio binary required")
    with tarfile.open(tgz, "r:gz") as tf:
        files: dict[str, bytes] = {}
        roots = set()
        total = 0
        for member in tf:
            p = PurePosixPath(member.name)
            if p.is_absolute() or ".." in p.parts or not (1 <= len(p.parts) <= 2):
                raise ValueError("unsafe tar path: " + member.name)
            roots.add(p.parts[0])
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError("symlink/device tar entry refused")
            if len(p.parts) != 2 or p.name not in _ALLOWED or p.name in files:
                raise ValueError("unexpected/duplicate updater member: " + member.name)
            if member.size <= 0 or member.size > 60_000_000:
                raise ValueError("empty/oversized updater member: " + p.name)
            total += member.size
            if total > max_total:
                raise ValueError("oversized updater package")
            fp = tf.extractfile(member)
            if fp is None:
                raise ValueError("unreadable updater member")
            files[p.name] = fp.read()
        if len(roots) != 1 or not next(iter(roots)).startswith("f7-update-"):
            raise ValueError("wrong Flipper target/updater directory")
        if not _REQUIRED.issubset(files):
            raise ValueError("missing radio, SD resources, DFU or updater stage")
        if _sha(files["firmware.dfu"]) != _sha(firmware.read_bytes()):
            raise ValueError("full TGZ embedded DFU differs from compiled firmware")
        if _sha(files["radio.bin"]) != _sha(radio.read_bytes()):
            raise ValueError("full TGZ embedded C2 radio differs from pinned firmware source")

        manifest = files["update.fuf"].decode("utf-8")
        fields: dict[str, str] = {}
        for line in manifest.splitlines():
            if ": " in line:
                k, v = line.split(": ", 1)
                if k in fields:
                    raise ValueError("duplicate updater manifest field: " + k)
                fields[k] = v.strip()
        for key, value in (
            ("Target", "7"),
            ("Firmware", "firmware.dfu"),
            ("Loader", "updater.bin"),
            ("Radio", "radio.bin"),
            ("Resources", "resources.tgz"),
        ):
            if fields.get(key) != value:
                raise ValueError("full updater manifest mismatch: " + key)
        if fields.get("Radio version", "").replace(" ", "").strip("0") == "":
            raise ValueError("missing nonzero radio version metadata")
        # A full official updater may contain option-byte masks from ob.data.
        # Do NOT claim zero option-byte changes or risk-free flashing.
        for key in ("OB reference", "OB mask", "OB write mask"):
            value = fields.get(key, "")
            if not value or len(value.split()) != 128:
                raise ValueError("unverified option-byte configuration: " + key)
            if any(len(x) != 2 or any(c not in "0123456789abcdefABCDEF" for c in x)
                   for x in value.split()):
                raise ValueError("malformed option-byte configuration: " + key)

        with tarfile.open(fileobj=io.BytesIO(files["resources.tgz"]), mode="r:gz") as resources:
            entries = resources.getmembers()
            if not entries:
                raise ValueError("empty SD resource archive")
            for m in entries:
                name = PurePosixPath(m.name)
                if name.is_absolute() or ".." in name.parts or not (m.isfile() or m.isdir()):
                    raise ValueError("unsafe SD resource entry")
        return {"dfu_sha256": _sha(files["firmware.dfu"]),
                "radio_sha256": _sha(files["radio.bin"]),
                "tgz_sha256": _sha(tgz.read_bytes()),
                "resource_members": len(entries),
                "option_bytes_mask": fields["OB write mask"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tgz", type=Path)
    parser.add_argument("dfu", type=Path)
    parser.add_argument("radio", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.tgz, args.dfu, args.radio)
    except (OSError, ValueError, UnicodeError, tarfile.TarError) as exc:
        parser.exit(1, "REFUSED: " + str(exc) + "\n")
    for key, value in result.items():
        print(f"{key}: {value}")
    print("FULL MOMENTUM UPDATE CONTENT AUDIT PASS; NOT A DEVICE/FLASH PASS")
