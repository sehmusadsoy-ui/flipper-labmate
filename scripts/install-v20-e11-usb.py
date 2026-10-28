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

from verify_v20_e11_debuglink_parity import verify_fap, IdentityFailure
EXPECTED="ddc27aa9e095c5ff809b000e4119d14151caf0d1a191c6a35c96f46ad1b01d72"
TARGET="/ext/apps/Tools/labmate.fap"

def discover_device_faps(device):
    """Read-only inventory of app file names/sizes; no device writes.

    Inspect /ext/apps and its immediate category folders, plus one nested
    level. Report likely previous LabMate builds and all Tools FAP names.
    A file name alone is not proof of app identity.
    """
    print("READ-ONLY DEVICE FAP SCAN: checking /ext/apps",flush=True)
    if not device.exist_dir("/ext/apps"):
        raise RuntimeError("NO-GO: /ext/apps missing, no device write")
    queue=[("/ext/apps",0)]
    visited=set()
    files=[]
    while queue:
        folder,level=queue.pop(0)
        if folder in visited:
            continue
        visited.add(folder)
        if len(visited)>90:
            raise RuntimeError("NO-GO: unexpectedly large apps directory inventory")
        print("READ-ONLY SCANNING:",folder,flush=True)
        # Momentum CLI protocol: storage list yields [D] and [F] lines.
        device.send_and_wait_eol('storage list "'+folder+'"\r')
        data=device.read.until(device.CLI_PROMPT)
        if device.has_error(data):
            raise RuntimeError("NO-GO: cannot list "+folder)
        for rawline in data.split(b"\r\n"):
            line=rawline.decode("utf-8","replace").strip()
            if line.startswith("[D] "):
                name=line[4:].strip()
                if level<2 and name not in (".","..") and "/" not in name and "\\" not in name:
                    queue.append((folder+"/"+name,level+1))
            elif line.startswith("[F] "):
                entry=line[4:].strip()
                try:
                    name,size=entry.rsplit(" ",1)
                except ValueError:
                    continue
                if name.lower().endswith(".fap") and size.isdigit():
                    files.append((folder+"/"+name,int(size)))
    print("READ-ONLY SCAN COMPLETE:",len(visited),"folders",flush=True)
    hits=[(p,n) for p,n in files if any(
        word in p.rsplit("/",1)[-1].lower()
        for word in ("labmate","lab_mate","counter-step3","ultimate")
    )]
    tools=[(p,n) for p,n in files if p.startswith("/ext/apps/Tools/")]
    print("DEVICE FAP INVENTORY (READ ONLY):",len(files),"FAP files across",len(visited),"folders")
    print("EXACT CANONICAL PRESENT:",any(p==TARGET for p,_ in files))
    for path,size in sorted(hits):
        print("LABMATE_CANDIDATE:",path,"bytes=",size)
    if not hits:
        print("NO MATCH BY FILE NAME. Filename alone does not identify the app.")
    for path,size in sorted(tools)[:120]:
        print("TOOLS_FAP:",path,"bytes=",size)
    if len(tools)>120:
        print("TOOLS_FAP_LIST_TRUNCATED:",len(tools)-120)
    print("DISCOVERY ONLY: no FAP readback backup, no install, no firmware write")
    return files

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--fap",type=Path,required=True)
    parser.add_argument("--backup-root",type=Path,required=True)
    parser.add_argument("--port",default="auto")
    parser.add_argument("--apply",action="store_true")
    parser.add_argument("--discover",action="store_true")
    args=parser.parse_args()
    if args.apply and args.discover:
        raise RuntimeError("NO-GO: --discover and --apply cannot be combined")
    if args.fap.name!="labmate.fap" or not args.fap.is_file():
        raise RuntimeError("NO-GO: local canonical labmate.fap missing")
    # The ONLY permitted difference from CI is a 4-byte debuglink CRC.
    # verify_fap checks every remaining byte against a pinned CI SHA256.
    actual_raw_sha=verify_fap(args.fap)
    new=args.fap.read_bytes()
    if hashlib.sha256(new).hexdigest()!=actual_raw_sha:
        raise RuntimeError("NO-GO: candidate changed during verification")
    if not args.apply and not args.discover:
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
        if args.discover:
            discover_device_faps(device)
            return 0
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
        print("NEW FAP SHA256:",actual_raw_sha)
        print("CI normalized verified SHA256:",EXPECTED)
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