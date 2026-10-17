#!/usr/bin/env python3
"""READ ONLY after E11 stage protocol abort: inspect original app and stage paths.

Uses ONLY device_info, storage stat, storage md5 on fixed allowlist.
No write_chunk, upload, rename, remove, GPIO, flash, reset or auto-retry.
IMPORTANT: An aborted upload can create an empty/partial nonapp SD sidecar.
An old FAP pass is not a staging PASS. Preserve evidence and STOP.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
import sys

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from check_v18_e11_final_fap_prewrite_ro import APP_REMOTE, pinned_local_expectation
from check_v18_e11_postupdate_readonly import REMOTE as POST_REMOTE, evaluate as verify_native
from check_v18_e11_h_js_runtime_ro import REMOTE as JS_REMOTE, compare_remote_identity as verify_js

STAGE = "/ext/apps/Tools/labmate.e11-new-stage"
BACKUP = "/ext/apps/Tools/labmate.e11-pre-final.bak"
PATHS = {APP_REMOTE, STAGE, BACKUP}
MISSING = b"Storage error: file/dir not exist"
FILE_SIZE = re.compile(rb"File, size: ([0-9]{1,8})b\Z")
CHECKSUM = re.compile(r"[a-f0-9]{32}\Z")
OLD_SIZE = 81532
NEW_SIZE = 81528


def stat_one(client, path: str) -> int | None:
    if path not in PATHS:
        raise ValueError("unapproved read-only stage status path")
    client.send_and_wait_eol(f'storage stat "{path}"\r')
    raw=client.read.until(client.CLI_EOL)
    tail=client.read.until(client.CLI_PROMPT)
    if tail.strip():
        raise ValueError("unrecognized storage stat framing")
    if raw==MISSING:
        return None
    m=FILE_SIZE.fullmatch(raw)
    if not m:
        raise ValueError("unrecognized file or storage response, stop")
    size=int(m.group(1))
    if size > 5_000_000:
        raise ValueError("oversized unexpected file")
    return size


def audit(client, post: dict[str,str], js: dict[str,str]) -> dict[str,str]:
    client.send_and_wait_eol("device_info\r")
    info=client.read.until(client.CLI_PROMPT)
    paths=dict(POST_REMOTE)
    paths.update({k:v for k,v in JS_REMOTE.items() if k not in paths})
    permitted={APP_REMOTE,"/ext/apps_data/js_app/plugins/js_gpio.fal",
               "/ext/apps_data/js_app/plugins/js_event_loop.fal","/ext/Manifest"}
    if set(paths.values())!=permitted:
        raise ValueError("remote identity scope differs from prior pinned E11")
    hashes={k:client.hash_flipper(path).strip() for k,path in paths.items()}
    verify_native(info,{k:hashes[k] for k in POST_REMOTE},post)
    verify_js(info,{k:hashes[k] for k in JS_REMOTE},js)
    if stat_one(client,APP_REMOTE)!=OLD_SIZE:
        raise ValueError("active old LabMate size differs; STOP")

    # Read only. On the first failed write the file may have been
    # opened in FSOM_OPEN_APPEND prior to the Python protocol abort.
    side_size=stat_one(client,STAGE)
    backup_size=stat_one(client,BACKUP)
    side_md5=None
    if side_size is not None:
        side_md5=client.hash_flipper(STAGE).strip().lower()
        if not CHECKSUM.fullmatch(side_md5):
            raise ValueError("unrecognized stage MD5; STOP")
    # Recheck the old app after stage reads; no writes under any condition.
    if client.hash_flipper(APP_REMOTE).strip().lower()!=post["E11_APP"]:
        raise ValueError("old app changed during diagnostic; STOP")
    if stat_one(client,APP_REMOTE)!=OLD_SIZE:
        raise ValueError("old app changed during diagnostic; STOP")
    result={
       "active_old_fap":"PINNED E11 SHA-BACKED MD5 + SIZE MATCH",
       "js_gpio_eventloop_manifest":"PINNED E11 MD5 MATCH",
       "reserved_backup_target":"ABSENT" if backup_size is None else "PRESENT — DO NOT TOUCH",
       "stage_status":(
          "ABSENT" if side_size is None else
          "PRESENT EMPTY 0 BYTES" if side_size==0 else
          f"PRESENT {side_size} BYTES (NOT ACCEPTED FOR INSTALL)"
       ),
       "stage_md5":side_md5 or "NOT APPLICABLE",
       "safe_to_retry_old_stage_script":"NO",
       "final_v18_fap_installed":"NO",
       "device_writes_performed_by_this_check":"NONE",
    }
    return result


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port",required=True)
    p.add_argument("--momentum-scripts",type=Path,required=True)
    p.add_argument("--old-candidate",type=Path,required=True)
    args=p.parse_args()
    print("E11 STAGE ABORT READ-ONLY DIAGNOSTIC - NO DEVICE WRITES")
    try:
        if not re.fullmatch(r"COM[1-9][0-9]{0,2}",args.port):
            raise ValueError("invalid exact COM port")
        post,js=pinned_local_expectation(args.old_candidate)
        scripts=args.momentum_scripts
        transport=scripts/"flipper"/"storage.py"
        if scripts.is_symlink() or transport.is_symlink() or not transport.is_file():
            raise ValueError("pinned Flipper serial transport not found")
        sys.path.insert(0,str(scripts.resolve()))
        import flipper.storage as sdk
        verify_transport_origin(sdk.__file__,scripts)
        cli=sdk.FlipperStorage(args.port)
        cli.read=DeadlineRead(cli.port,timeout_seconds=15)
        with cli as connected:
            result=audit(connected,post,js)
    except Exception as exc:
        why=str(exc) if type(exc)==ValueError else type(exc).__name__
        print("E11 STAGE ABORT DIAGNOSTIC INCOMPLETE: "+why,file=sys.stderr)
        print("STOP. DO NOT RESET, RETRY, DELETE, RENAME OR LOAD FAP.",file=sys.stderr)
        return 1
    for key,value in result.items():
        print(key+": "+value)
    print("E11 STAGE ABORT READ-ONLY STATE RECORDED — NO RETRY OR FAP PROMOTION")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
