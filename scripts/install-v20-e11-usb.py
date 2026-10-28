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
import re
from pathlib import Path
import sys

from verify_v20_e11_debuglink_parity import verify_fap, IdentityFailure
EXPECTED="ddc27aa9e095c5ff809b000e4119d14151caf0d1a191c6a35c96f46ad1b01d72"
TARGET="/ext/apps/Tools/labmate.fap"

def discover_device_faps(device):
    """Read-only inventory of legacy FAP paths; no device writes.

    The old parser silently discarded every file whose listing had a
    non-decimal size suffix. Report raw directory evidence and count files
    separately from successfully recognized .fap entries; never infer that
    the device has no apps from an empty parsed list.
    """
    print("READ-ONLY DEVICE FAP SCAN: checking /ext/apps",flush=True)
    if not device.exist_dir("/ext/apps"):
        raise RuntimeError("NO-GO: /ext/apps missing, no device write")
    queue=[("/ext/apps",0)]
    visited=set()
    files=[]
    raw_files=0
    unrecognized=[]
    sample=[]
    while queue:
        folder,level=queue.pop(0)
        if folder in visited:
            continue
        visited.add(folder)
        if len(visited)>90:
            raise RuntimeError("NO-GO: unexpectedly large apps directory inventory")
        print("READ-ONLY SCANNING:",folder,flush=True)
        device.send_and_wait_eol('storage list "'+folder+'"\r')
        data=device.read.until(device.CLI_PROMPT)
        if device.has_error(data):
            raise RuntimeError("NO-GO: cannot list "+folder)
        for rawline in data.split(b"\r\n"):
            line=rawline.decode("utf-8","replace").strip()
            if folder == "/ext/apps/Tools" and len(sample)<60 and line:
                sample.append(line[:250])
            if line.startswith("[D] "):
                name=line[4:].strip()
                if level<2 and name not in (".","..") and "/" not in name and "\\" not in name:
                    queue.append((folder+"/"+name,level+1))
            elif line.startswith("[F] "):
                raw_files+=1
                entry=line[4:].strip()
                # Accept size fields that are missing, have suffixes/units,
                # or include additional words; they are for display only.
                match=re.match(r"(?is)^(.+?\.fap)(?:\s+(.*))?$",entry)
                if match:
                    name=match.group(1)
                    size_field=(match.group(2) or "?").strip()
                    size=int(size_field) if size_field.isdigit() else size_field
                    files.append((folder+"/"+name,size))
                elif len(unrecognized)<24:
                    unrecognized.append((folder,line[:250]))
    print("READ-ONLY SCAN COMPLETE:",len(visited),"folders",flush=True)
    print("RAW FILE LISTING ROWS:",raw_files)
    print("RECOGNIZED FAP ROWS:",len(files))
    print("RAW TOOLS DIRECTORY SAMPLE (MAX 60 ROWS):")
    for line in sample:
        print("RAW_TOOLS_ENTRY:",repr(line))
    if not sample:
        print("RAW_TOOLS_EMPTY: No nonempty CLI listing lines for /ext/apps/Tools")
    for path,line in unrecognized:
        print("UNRECOGNIZED_FILE_ENTRY:",path,repr(line))
    hits=[(p,n) for p,n in files if any(
        word in p.rsplit("/",1)[-1].lower()
        for word in ("labmate","lab_mate","counter-step3","ultimate")
    )]
    tools=[(p,n) for p,n in files if p.startswith("/ext/apps/Tools/")]
    print("DEVICE FAP INVENTORY (READ ONLY):",len(files),"FAP files across",len(visited),"folders")
    print("EXACT CANONICAL PRESENT:",any(p==TARGET for p,_ in files))
    for path,size in sorted(hits):
        print("LABMATE_CANDIDATE:",path,"size_listing=",size)
    if not hits:
        print("NO MATCH BY FILE NAME; not proof that no LabMate exists.")
    for path,size in sorted(tools)[:120]:
        print("TOOLS_FAP:",path,"size_listing=",size)
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
        # Momentum's native CLI prints '[F] name.fap 12345b'.
        # List all apps in THIS same USB session; don't equate a missing
        # canonical filename with a missing previously tested LabMate.
        inventory=discover_device_faps(device)
        all_paths={p for p,_ in inventory}
        target_exists=device.exist_file(TARGET)
        if target_exists and TARGET not in all_paths:
            raise RuntimeError("NO-GO: canonical FAP stat/list disagreement")
        # An extra legacy candidate alongside canonical is a duplicate.
        # Refuse an ambiguous migration instead of overwriting an app.
        candidates=sorted(
            p for p,_ in inventory if p!=TARGET and any(
                tag in p.rsplit("/",1)[-1].lower()
                for tag in ("labmate","lab_mate","lab-mate","lab mate","counter-step3")
            )
        )
        if len(candidates)>1 or (target_exists and candidates):
            for p in candidates:
                print("AMBIGUOUS LEGACY FAP:",p,flush=True)
            raise RuntimeError("NO-GO: multiple LabMate files; refuse ambiguous replacement")
        if target_exists:
            old_path=TARGET
            mode="REPLACE CANONICAL"
        elif candidates:
            old_path=candidates[0]
            mode="MIGRATE LEGACY TO CANONICAL"
        else:
            old_path=None
            mode="FIRST INSTALL (no LabMate filename found)"
        print("INSTALL PLAN:",mode,flush=True)
        print("INSTALL TARGET:",TARGET,flush=True)
        old=None
        old_md5=None
        saved=None
        if old_path is not None:
            print("SOURCE FAP:",old_path,flush=True)
            if not device.exist_file(old_path):
                raise RuntimeError("NO-GO: listed old FAP has disappeared")
            old=bytes(device.read_file(old_path))
            if len(old)<64 or old[:4]!=b"\x7fELF":
                raise RuntimeError("NO-GO: old FAP does not have expected ELF signature")
            old_md5=hashlib.md5(old).hexdigest()
            if device.hash_flipper(old_path).strip().lower()!=old_md5:
                raise RuntimeError("NO-GO: original USB readback differs from device MD5")
            root=args.backup_root.resolve()
            root.mkdir(parents=True,exist_ok=True)
            folder=root/("before-v20-e11-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
            folder.mkdir(exist_ok=False)
            saved=folder/old_path.rsplit("/",1)[-1]
            with saved.open("xb") as stream:
                stream.write(old)
                stream.flush()
                os.fsync(stream.fileno())
            if saved.read_bytes()!=old:
                raise RuntimeError("NO-GO: original PC backup verification failure")
            print("OLD FAP SAVED TO PC:",saved,flush=True)
            print("OLD FAP SHA256:",hashlib.sha256(old).hexdigest(),flush=True)
            if old_md5==hashlib.md5(new).hexdigest() and old_path==TARGET:
                print("EXACT NEW FAP ALREADY INSTALLED. No device write.")
                return 0
        else:
            print("NO PREVIOUS LABMATE FAP FOUND BY NAME; first install requires consent.",flush=True)
        print("NEW FAP SHA256:",actual_raw_sha,flush=True)
        print("CI normalized verified SHA256:",EXPECTED,flush=True)
        # Firmware API version alone is NOT proof of patched resource ABI.
        fields={}
        for line in firmware:
            if ":" in line:
                k,v=line.split(":",1)
                fields[k.strip()]=v.strip()
        if (fields.get("firmware_commit")!="d3f89dfe"
            or fields.get("firmware_api_major")!="87"
            or fields.get("firmware_api_minor")!="1"
            or fields.get("firmware_commit_dirty")!="true"):
            raise RuntimeError("NO-GO: device firmware identity differs from audited dirty E11")
        print("CAUTION: firmware identity does NOT prove exact custom E11 resource ABI.")
        print("Only approve if this is your previously tested PATCHED Momentum E11.")
        if old_path is None:
            print("NO ORIGINAL FAP TO BACK UP. Verify your old app was intentionally removed.")
        elif old_path!=TARGET:
            print("AFTER successful NEW FAP readback, legacy device file will be removed:")
            print("  ",old_path)
            print("The VERIFIED original remains in PC backup:",saved)
        print("Firmware, GPIO, CSV and profile files will NOT be modified.")
        if input("Type YUKLE-E11-LABMATE to approve the above one-FAP plan: ").strip()!="YUKLE-E11-LABMATE":
            raise RuntimeError("NO-GO: operator declined installation")
        if old_path is not None:
            if not device.exist_file(old_path) or device.hash_flipper(old_path).strip().lower()!=old_md5:
                raise RuntimeError("NO-GO: old FAP changed since verified PC backup")
            if saved is None or saved.read_bytes()!=old:
                raise RuntimeError("NO-GO: original backup disappeared or changed")
        if old_path!=TARGET and device.exist_file(TARGET):
            raise RuntimeError("NO-GO: canonical destination appeared after discovery")
        # Refuse writing FAP while any app is running. Asking the user to
        # leave the app is safer than forcibly closing unknown foreground apps.
        loader=device.send_and_wait_prompt("loader info\r")
        if b"No application is running" not in loader:
            raise RuntimeError("NO-GO: close running application on Flipper before install")
        # FlipperStorage.send_file deletes/replaces the TARGET if present.
        # With legacy migration, old file is untouched until NEW file MD5 PASS.
        device.send_file(str(args.fap),TARGET)
        if (device.size(TARGET)!=len(new)
            or device.hash_flipper(TARGET).strip().lower()!=hashlib.md5(new).hexdigest()):
            raise RuntimeError("NO-GO: installed FAP size/MD5 differ; DO NOT RETRY")
        print("NEW CANONICAL FAP DEVICE READBACK PASS:",TARGET,flush=True)
        if old_path is not None and old_path!=TARGET:
            if saved is None or saved.read_bytes()!=old:
                raise RuntimeError("NO-GO: old FAP PC backup changed; legacy left intact")
            if device.hash_flipper(old_path).strip().lower()!=old_md5:
                raise RuntimeError("NO-GO: legacy device FAP changed; legacy left intact")
            device.remove(old_path)
            if device.exist_file(old_path):
                raise RuntimeError("NO-GO: legacy cleanup unverified; PC backup preserved")
            print("LEGACY FAP CLEANUP PASS:",old_path,flush=True)
        print("USB SINGLE FAP WRITE/READBACK PASS:",TARGET)
        print("Physical Button/Scope/UI tests NOT YET PERFORMED")
        return 0

if __name__=="__main__":
    try:sys.exit(main())
    except (Exception,KeyboardInterrupt) as exc:
        print("LabMate E11 STOP:",exc,file=sys.stderr)
        sys.exit(1)