#!/usr/bin/env python3
"""E11 v1.8 FAP stage-only from an *already verified EMPTY* nonapp SD file.

No remove/rename/replace, never target installed /ext/apps/Tools/labmate.fap.
A different named backup/new staging file, or even 1 already-written byte
is NO-GO. Send candidate bytes only after validating exact old FAP PC backup,
actual old device resources, and the pre-existing empty stage MD5.
No automatic retry or stage deletion even on a partial transfer.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from check_v18_e11_final_fap_prewrite_ro import pinned_local_expectation, APP_REMOTE
from check_v18_e11_postupdate_readonly import REMOTE as POST_REMOTE, evaluate as compare_resources
from check_v18_e11_h_js_runtime_ro import REMOTE as JS_REMOTE, compare_remote_identity as compare_js
from stage_v18_final_fap_on_device_one_file import (
    STAGE, OLD_BACKUP_TARGET, NEW_SIZE, BUF, MISSING,
    local_preflight, checked_stat, append_staged_chunk, NEW_FAP_SHA, EXPECTED_SHA,
)

EMPTY_MD5 = "d41d8cd98f00b204e9800998ecf8427e"
OLD_STAT = b"File, size: 81532b"
EMPTY_STAT = b"File, size: 0b"
NEW_STAT = b"File, size: 81528b"


def check_old_and_empty_stage(client, post: dict[str,str], js: dict[str,str]) -> None:
    client.send_and_wait_eol("device_info\r")
    info=client.read.until(client.CLI_PROMPT)
    paths=dict(POST_REMOTE)
    paths.update({k:v for k,v in JS_REMOTE.items() if k not in paths})
    if set(paths.values()) != {
        APP_REMOTE,
        "/ext/apps_data/js_app/plugins/js_gpio.fal",
        "/ext/apps_data/js_app/plugins/js_event_loop.fal",
        "/ext/Manifest"
    }:
        raise ValueError("unrecognized resource allowlist")
    md5={k:client.hash_flipper(path).strip() for k,path in paths.items()}
    compare_resources(info,{k:md5[k] for k in POST_REMOTE},post)
    compare_js(info,{k:md5[k] for k in JS_REMOTE},js)
    if checked_stat(client, APP_REMOTE) != OLD_STAT:
        raise ValueError("active old E11 FAP size changed")
    if checked_stat(client, STAGE) != EMPTY_STAT:
        raise ValueError("stage is NOT exactly zero bytes; never append/retry")
    if client.hash_flipper(STAGE).strip().lower() != EMPTY_MD5:
        raise ValueError("stage is NOT empty by device MD5; never append/retry")
    if checked_stat(client, OLD_BACKUP_TARGET) != MISSING:
        raise ValueError("reserved old-FAP backup destination no longer absent")
    if client.hash_flipper(APP_REMOTE).strip().lower()!=post["E11_APP"]:
        raise ValueError("active old FAP MD5 changed during preflight")


def resume_once(client, blob: bytes, post: dict[str,str], js: dict[str,str]) -> dict[str,str]:
    if not isinstance(blob,bytes) or len(blob)!=NEW_SIZE or hashlib.sha256(blob).hexdigest()!=NEW_FAP_SHA:
        raise ValueError("unrecognized exact new candidate")
    check_old_and_empty_stage(client,post,js)
    total=0
    for off in range(0,len(blob),BUF):
        piece=blob[off:off+BUF]
        append_staged_chunk(client,piece)
        total+=len(piece)
        # Every chunk is independently followed by a stat. The file remains
        # non-app; if there is a partial write, fail and NEVER auto-retry.
        expected=f"File, size: {total}b".encode("ascii")
        if checked_stat(client,STAGE)!=expected:
            raise ValueError("staged length != acknowledged chunk length; STOP")
    if total != NEW_SIZE or checked_stat(client,STAGE)!=NEW_STAT:
        raise ValueError("exact 81528-byte staging not observed")
    expected_md5=hashlib.md5(blob).hexdigest()
    if client.hash_flipper(STAGE).strip().lower()!=expected_md5:
        raise ValueError("staged FAP device MD5 differs from exact reviewed PC file")
    if checked_stat(client,APP_REMOTE)!=OLD_STAT:
        raise ValueError("old active LabMate FAP stat changed")
    if client.hash_flipper(APP_REMOTE).strip().lower()!=post["E11_APP"]:
        raise ValueError("old active LabMate FAP MD5 changed")
    for key,path in JS_REMOTE.items():
        if key=="labmate.fap":
            continue
        if client.hash_flipper(path).strip().lower()!=js[key]:
            raise ValueError("native JS module changed: "+key)
    if client.hash_flipper("/ext/Manifest").strip().lower()!=post["E11_NEW_MANIFEST"]:
        raise ValueError("Manifest MD5 changed")
    if checked_stat(client,OLD_BACKUP_TARGET)!=MISSING:
        raise ValueError("old backup destination changed")
    if checked_stat(client,STAGE)!=NEW_STAT:
        raise ValueError("staged FAP size changed after final checks")
    return {
        "stage_fap":"SHA-BACKED DEVICE MD5 / SIZE MATCH",
        "stage_path":STAGE,
        "stage_md5":expected_md5,
        "stage_bytes":str(NEW_SIZE),
        "active_old_labmate":"PINNED OLD MD5 + SIZE UNCHANGED",
        "native_js_manifest":"PINNED RESOURCE MD5 UNCHANGED",
        "old_pc_backup":"PINNED VERIFIED",
        "new_v18_fap_installed":"NO",
        "firmware_flash":"NO",
        "stage_update":"ONLY EXISTING EMPTY NONAPP SIDECAR",
        "automatic_retry_or_cleanup":"NEVER",
    }


def perform(port: str, transport: Path, old_candidate: Path,
            backup: Path, new_fap: Path) -> dict[str,str]:
    if not re.fullmatch(r"COM[1-9][0-9]{0,2}",port):
        raise ValueError("invalid exact COMn port")
    blob=local_preflight(new_fap,backup,old_candidate)
    post,js=pinned_local_expectation(old_candidate)
    module=transport/"flipper"/"storage.py"
    if transport.is_symlink() or module.is_symlink() or not module.is_file():
        raise ValueError("trusted pinned native serial transport unavailable")
    sys.path.insert(0,str(transport.resolve()))
    import flipper.storage as sdk
    verify_transport_origin(sdk.__file__,transport)
    c=sdk.FlipperStorage(port)
    c.read=DeadlineRead(c.port,timeout_seconds=20)
    c.port.write_timeout=12
    with c as cli:
        return resume_once(cli,blob,post,js)


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port",required=True)
    p.add_argument("--momentum-scripts",type=Path,required=True)
    p.add_argument("--old-candidate",type=Path,required=True)
    p.add_argument("--saved-old-fap-backup",type=Path,required=True)
    p.add_argument("--new-fap",type=Path,required=True)
    args=p.parse_args()
    print("E11 v1.8 2A: ONE-SHOT APPEND INTO VERIFIED EXISTING ZERO-BYTE NONAPP STAGE")
    print("NO OLD APP REPLACEMENT, RENAME, REMOVE, MANIFEST OR FIRMWARE WRITE.")
    try:
        report=perform(args.port,args.momentum_scripts,args.old_candidate,
                       args.saved_old_fap_backup,args.new_fap)
    except Exception as exc:
        reason=str(exc) if type(exc)==ValueError else type(exc).__name__
        print("E11 v1.8 EXISTING-EMPTY-STAGE NO-GO: "+reason,file=sys.stderr)
        print("STOP; DO NOT RERUN, REMOVE, RENAME, FLASH OR AUTO-RECOVER.",file=sys.stderr)
        return 1
    for key,value in report.items():
        print(key+": "+value)
    print("E11 v1.8 EXISTING EMPTY STAGE FULL VERIFIED PASS - OLD APP PRESERVED")
    print("STOP; PHASE 2B APPLICATION PROMOTION NOT PERFORMED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
