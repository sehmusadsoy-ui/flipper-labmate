#!/usr/bin/env python3
"""Prepare the exact, already-verified E11 updater for HUMAN REVIEW ONLY.

OFFLINE only: no Flipper USB, storage CLI, serial, firmware flash, FAP
installation, rollback, SD modification, qFlipper or updater execution.
A review artifact labeled DO NOT FLASH cannot be turned into an
authorized installer by running this script.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import tarfile

from preflight_v18_e11_local import preflight, ARTIFACTS
from verify_v18_full_review_pair import OFFICIAL_RADIO_SHA256

ROOT = "f7-update-mntm-HEAD-d3f89dfe"
FILES = (
    "firmware.dfu", "firstboot.bin", "radio.bin", "resources.tar.gz",
    "splash.bin", "update.fuf", "updater.bin",
)
MAX_FILE = 60_000_000
MAX_TOTAL = 90_000_000
WARNING = (
    "REVIEW ONLY - DO NOT FLASH, INSTALL, APPLY, OR RELEASE.\n"
    "Not physically accepted. Restore NOT rehearsed.\n"
    "Exact candidate: full CI run 38966248325, source ba379f20fb29369501e1057f570a911f71ac83f8.\n"
    "A separate recovery review and explicit owner approval are necessary.\n"
    "DO NOT use the old installer pinned to a different firmware/FAP pair.\n"
)


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect_updater(tgz: Path, *,
                    expected_dfu: str = ARTIFACTS["firmware.dfu"],
                    expected_radio: str = OFFICIAL_RADIO_SHA256) -> dict[str, bytes]:
    """Load only a strictly allowlisted full updater. Never extract TAR paths."""
    if tgz.is_symlink() or not tgz.is_file():
        raise ValueError("missing or linked firmware updater archive")
    members: dict[str, bytes] = {}
    seen_root = False
    total = 0
    with tarfile.open(tgz, mode="r:gz") as tf:
        for m in tf:
            name = m.name
            if m.isdir() and name.rstrip("/") == ROOT and not seen_root:
                seen_root = True
                continue
            if not m.isfile() or name not in {ROOT + "/" + f for f in FILES}:
                raise ValueError("refusing unexpected TAR member/type")
            simple = name[len(ROOT) + 1:]
            if simple in members:
                raise ValueError("refusing duplicate updater member")
            if m.size <= 0 or m.size > MAX_FILE:
                raise ValueError("refusing empty or oversized updater member")
            total += m.size
            if total > MAX_TOTAL:
                raise ValueError("refusing oversized updater archive")
            stream = tf.extractfile(m)
            if stream is None:
                raise ValueError("unreadable updater archive member")
            body = stream.read(m.size + 1)
            if len(body) != m.size:
                raise ValueError("truncated updater archive member")
            members[simple] = body
    if set(members) != set(FILES):
        raise ValueError("refusing incomplete updater files")
    if _hash(members["firmware.dfu"]) != expected_dfu:
        raise ValueError("embedded firmware.dfu is not exact approved-for-review bytes")
    if _hash(members["radio.bin"]) != expected_radio:
        raise ValueError("embedded radio.bin not official known reference bytes")
    return members


def write_review_stage(output: Path, files: dict[str, bytes]) -> Path:
    """Write to a NEW local folder only. No -force/overwrite/remove behavior."""
    if output.exists() or output.is_symlink():
        raise ValueError("review output already exists - refusing overwrite")
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError("review output parent must be an existing real directory")
    if set(files) != set(FILES):
        raise ValueError("review files missing/extra")
    # A clearly labeled safe wrapper is the only output created.
    output.mkdir(mode=0o700)
    (output / "STAGING_REVIEW_ONLY.txt").write_text(WARNING, encoding="utf-8")
    dest = output / ROOT
    dest.mkdir(mode=0o700)
    for name in FILES:
        (dest / name).write_bytes(files[name])
    for name in FILES:
        if _hash((dest / name).read_bytes()) != _hash(files[name]):
            raise ValueError("stage disk write verification failed")
    return dest


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--rollback", type=Path, required=True)
    p.add_argument("--installed-fap-copy", type=Path, required=True)
    p.add_argument("--data-backup", type=Path, required=True)
    p.add_argument("--settings-archive", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True,
                   help="brand-new LOCAL review directory; never a Flipper storage path")
    args = p.parse_args()
    try:
        # Prevent any output before ALL upstream provenance/backup checks pass.
        preflight(args.candidate, args.rollback, args.installed_fap_copy,
                  args.data_backup, args.settings_archive)
        print("EXACT E11 CANDIDATE AND BACKUP PREFLIGHT PASS (OFFLINE)")
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("review output already exists")
        files = inspect_updater(args.candidate / "firmware-full-update.tgz")
        output = write_review_stage(args.output, files)
    except (OSError, ValueError, UnicodeError, tarfile.TarError) as exc:
        p.exit(1, "E11 REVIEW STAGING REFUSED - NO DEVICE WRITE: " + str(exc) + "\n")
    print("REVIEW-ONLY UPDATER FILES: " + str(len(FILES)))
    print("REVIEW DIRECTORY: " + str(output))
    print("E11 LOCAL REVIEW STAGING PASS - NOT AUTHORIZED TO FLASH")
    print("No Flipper connection, firmware install, FAP overwrite, SD operation or restore.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
