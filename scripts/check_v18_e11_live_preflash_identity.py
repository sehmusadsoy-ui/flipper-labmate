#!/usr/bin/env python3
"""Fail closed against a changed/wrong Flipper immediately before E11 trial.

Device operations: pinned Flipper CLI startup device_info, a second device_info,
and storage md5 on /ext/apps/Tools/labmate.fap only. No writes, resets or flash.
The prior custom firmware is not byte-authenticated; this is an identity screen.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin

EXPECTED_VERSION = "mntm-dev"
EXPECTED_BASE = "d3f89dfe"
EXPECTED_EXITFIX_SHA256 = "7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be"
FAP = "/ext/apps/Tools/labmate.fap"
MD5 = re.compile(r"[0-9a-fA-F]{32}\Z")


def screen_identity(raw: bytes, reported_fap_md5: str, saved_fap: bytes) -> None:
    """Compares live, read-only device claims with independently verified PC bytes."""
    if not isinstance(raw, bytes) or len(raw) > 131072:
        raise ValueError("invalid device_info size")
    try:
        report = raw.decode("utf-8", errors="strict").lower()
    except UnicodeDecodeError:
        raise ValueError("device_info is not valid UTF-8") from None
    if EXPECTED_VERSION not in report or EXPECTED_BASE not in report:
        raise ValueError("unexpected Flipper firmware/version: DO NOT FLASH")
    if hashlib.sha256(saved_fap).hexdigest() != EXPECTED_EXITFIX_SHA256:
        raise ValueError("saved EXITFIX copy has changed")
    if not isinstance(reported_fap_md5, str) or not MD5.fullmatch(reported_fap_md5):
        raise ValueError("invalid live FAP MD5")
    if hashlib.md5(saved_fap).hexdigest() != reported_fap_md5.lower():
        raise ValueError("device EXITFIX differs from preserved PC readback")


def check_device(port: str, scripts: Path, installed_fap: Path) -> None:
    if not re.fullmatch(r"COM[1-9][0-9]{0,2}", port):
        raise ValueError("explicit COMn port required")
    expected_transport = scripts / "flipper" / "storage.py"
    if (scripts.is_symlink() or expected_transport.is_symlink() or
            not expected_transport.is_file()):
        raise ValueError("missing pinned Momentum transport")
    if installed_fap.is_symlink() or not installed_fap.is_file():
        raise ValueError("missing saved EXITFIX")
    # Fail before USB/serial open if local EXITFIX is not the reviewed readback.
    filedata = installed_fap.read_bytes()
    if hashlib.sha256(filedata).hexdigest() != EXPECTED_EXITFIX_SHA256:
        raise ValueError("wrong saved EXITFIX SHA256")
    sys.path.insert(0, str(scripts.resolve()))
    import flipper.storage as flipper_storage
    verify_transport_origin(flipper_storage.__file__, scripts)
    device = flipper_storage.FlipperStorage(port)
    device.read = DeadlineRead(device.port, timeout_seconds=20.0)
    with device as connected:
        connected.send_and_wait_eol("device_info\r")
        identity = connected.read.until(connected.CLI_PROMPT)
        md5 = connected.hash_flipper(FAP).strip()
        screen_identity(identity, md5, filedata)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", required=True)
    p.add_argument("--momentum-scripts", type=Path, required=True)
    p.add_argument("--installed-exitfix-copy", type=Path, required=True)
    args = p.parse_args()
    try:
        check_device(args.port, args.momentum_scripts, args.installed_exitfix_copy)
    except Exception as error:
        # Never print device private identifiers or raw serial contents.
        name = str(error) if type(error) is ValueError else type(error).__name__
        print("E11 LIVE IDENTITY REFUSED - NO FLASH: " + name, file=sys.stderr)
        return 1
    print("E11 READ-ONLY LIVE IDENTITY SCREEN PASS - NO DEVICE WRITE")
    print("Firmware reports expected custom base; current installed FAP MD5 matches preserved EXITFIX bytes.")
    print("NOT a full firmware fingerprint, not rollback proof, not boot acceptance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
