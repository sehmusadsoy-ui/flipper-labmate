#!/usr/bin/env python3
"""Single-canonical-FAP USB transfer. PC-backup readback before any write.
Never flashes firmware or touches CSV/Profile files. Requires explicit
operator approval of the existing device's patched Momentum E11 match.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sys

EXPECTED="6dbe192ba7d1b0f2b05702c90cf68d791f041f75ed53a6b41135176b6ad4de5b"
TARGET="/ext/apps/Tools/labmate.fap"

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--fap",type=Path,required=True)
    parser.add_argument("--backup-root",type=Path,required=True)
    parser.add_argument("--port",default="auto")
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    if args.fap.name!="labmate.fap" or not args.fap.is_file():
        raise RuntimeError("NO-GO: local canonical labmate.fap missing")
    new=args.fap.read_bytes()
    if len(new)!=174192 or hashlib.sha256(new).hexdigest()!=EXPECTED:
        raise RuntimeError("NO-GO: candidate SHA-256 or size differs from GitHub E11 CI")
    if new[:4]!=b"\x7fELF":
        raise RuntimeError("NO-GO: candidate is not an ELF FAP")
    if not args.apply:
        print("EXACT FAP PC-ONLY VERIFY PASS. No USB write.")
        return 0

    import logging
    from flipper.storage import FlipperStorage
    from flipper.utils.cdc import resolve_port
    port=resolve_port(logging.getLogger("LabMate"),args.port)
    if not port:raise RuntimeError("NO-GO: COM port not found")
    with FlipperStorage(port) as device:
        info=device.send_and_wait_prompt("device_info\r").decode("ascii","replace")
        firmware=[line.strip() for line in info.splitlines()
                  if "firmware" in line.lower() or "hardware_model" in line.lower()]
        for line in firmware[:18]:print("DEVICE:",line)
        if not any("mntm" in line.lower() or "momentum" in line.lower() for line in firmware):
            raise RuntimeError("NO-GO: expected Momentum firmware identity absent")
        if not device.exist_file(TARGET):
            raise RuntimeError("NO-GO: no existing canonical FAP; refuse new install")
        old=device.read_file(TARGET)
        if len(old)<64 or old[:4]!=b"\x7fELF":
            raise RuntimeError("NO-GO: existing FAP is not valid ELF")
        old_md5=hashlib.md5(old).hexdigest()
        if device.hash_flipper(TARGET).strip().lower()!=old_md5:
            raise RuntimeError("NO-GO: original USB readback differs from device MD5")
        root=args.backup_root.resolve()
        root.mkdir(parents=True,exist_ok=True)
        folder=root/("before-v20-e11-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
        folder.mkdir(exist_ok=False)
        saved=folder/"labmate.fap"
        with saved.open("xb") as f:
            f.write(old)
            f.flush()
            os.fsync(f.fileno())
        if saved.read_bytes()!=old:
            raise RuntimeError("NO-GO: PC original backup verification failure")
        print("OLD FAP SAVED TO PC:",saved)
        print("OLD FAP SHA256:",hashlib.sha256(old).hexdigest())
        print("NEW FAP SHA256:",EXPECTED)
        if old_md5==hashlib.md5(new).hexdigest():
            print("EXACT NEW FAP ALREADY INSTALLED. No device write.")
            return 0
        print("CAUTION: device_info does NOT independently prove matched E11 custom ABI.")
        print("Confirm the device is running the same previously tested PATCHED E11.")
        if input("Type YUKLE-E11-LABMATE for ONE FAP replacement: ").strip()!="YUKLE-E11-LABMATE":
            raise RuntimeError("NO-GO: operator declined installation")
        if device.hash_flipper(TARGET).strip().lower()!=old_md5:
            raise RuntimeError("NO-GO: device FAP changed since backup")
        for _ in range(10):
            device.send_and_wait_eol("loader close\r")
            result=device.read.until(device.CLI_EOL)
            if b"was closed" in result:
                device.read.until(device.CLI_EOL)
            elif result.startswith(b"No application"):
                device.read.until(device.CLI_EOL)
                break
            else:
                raise RuntimeError("NO-GO: unexpected foreground app result")
        else:
            raise RuntimeError("NO-GO: app remains running")
        # Sends ONLY TARGET; do not retry or self-rollback on error.
        device.send_file(str(args.fap),TARGET)
        if device.size(TARGET)!=len(new) or device.hash_flipper(TARGET).strip().lower()!=hashlib.md5(new).hexdigest():
            raise RuntimeError("NO-GO: installed FAP size/MD5 differ; DO NOT RETRY")
        print("USB SINGLE FAP WRITE/READBACK PASS:",TARGET)
        print("Physical Button/Scope/UI tests NOT YET PERFORMED")
        return 0

if __name__=="__main__":
    try:sys.exit(main())
    except (Exception,KeyboardInterrupt) as exc:
        print("LabMate E11 STOP:",exc,file=sys.stderr)
        sys.exit(1)