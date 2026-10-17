#!/usr/bin/env python3
"""LabMate E11 PHASE 2B: exact verified FAP-only promotion, two safe renames.

REAL DEVICE WRITE CAPABILITY: ONLY TWO predeclared same-directory renames:
  1. active labmate.fap -> labmate.e11-pre-final.bak
  2. verified labmate.e11-new-stage -> active labmate.fap

This script MUST NOT be provided as an operator command until independent
host mock CI and exact Momentum source audit are accepted. It is an
independently reviewed proposal, NOT Stable publication or full flash.

After first rename and before second: LabMate FAP is TEMPORARILY absent
from the normal app path; the exact original remains under .bak (plus
the immutable separately-verified PC backup). If any step fails,
STOP: NO AUTOMATIC ROLLBACK OR RETRY. Manual recover later only with
fresh read-only evidence and explicit permission.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from check_v18_e11_final_fap_prewrite_ro import (
    APP_REMOTE, EXPECTED_BYTES, EXPECTED_SHA, NEW_FAP_SHA, pinned_local_expectation
)
from check_v18_e11_h_js_runtime_ro import (
    REMOTE as JS_REMOTE, compare_remote_identity as check_js
)
from check_v18_e11_postupdate_readonly import (
    REMOTE as POST_REMOTE, evaluate as check_resources
)
from stage_v18_final_fap_on_device_one_file import (
    STAGE, OLD_BACKUP_TARGET as BACKUP, NEW_SIZE, local_preflight
)

ABSENT = b"Storage error: file/dir not exist"
OLD_SIZE = b"File, size: 81532b"
NEW_SIZE_LINE = b"File, size: 81528b"
ALLOW={APP_REMOTE,BACKUP,STAGE}
OLD_NAME = "/ext/apps/Tools/labmate.fap"
if APP_REMOTE != OLD_NAME:
    raise ValueError("source code changed active LabMate path unexpectedly")


def stat(client, path: str) -> bytes:
    if path not in ALLOW:
        raise ValueError("forbidden remote stat path")
    cmd = f'storage stat "{path}"'
    echoed = client.send_and_wait_eol(cmd + "\r")
    if echoed != cmd.encode("ascii"):
        raise ValueError("unexpected CLI stat command echo")
    value = client.read.until(client.CLI_EOL)
    tail = client.read.until(client.CLI_PROMPT)
    if tail != b"\r\n":
        raise ValueError("unrecognized trailing CLI stat response")
    if value not in (ABSENT,OLD_SIZE,NEW_SIZE_LINE):
        raise ValueError("unrecognized size / error from fixed stat path")
    return value


def exact_md5(client, path: str, expected: str) -> None:
    if path not in ALLOW and path not in set(POST_REMOTE.values()) | set(JS_REMOTE.values()):
        raise ValueError("forbidden remote checksum path")
    digest = client.hash_flipper(path).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{32}",digest) or digest != expected:
        raise ValueError("pinned remote MD5 mismatch on named resource: "+path)


def native_checks(client, post: dict[str,str], js: dict[str,str]) -> None:
    for name,path in JS_REMOTE.items():
        if path == APP_REMOTE:
            continue
        exact_md5(client,path,js[name])
    exact_md5(client,"/ext/Manifest",post["E11_NEW_MANIFEST"])


def rename_once(client, source: str, target: str) -> None:
    allowed_moves={(APP_REMOTE,BACKUP),(STAGE,APP_REMOTE)}
    if (source,target) not in allowed_moves:
        raise ValueError("forbidden storage rename scope")
    if stat(client,source) == ABSENT:
        raise ValueError("source disappeared before protected rename")
    if stat(client,target) != ABSENT:
        raise ValueError("rename target exists or is ambiguous")
    cmd = f'storage rename "{source}" "{target}"'
    echo = client.send_and_wait_eol(cmd+"\r")
    if echo != cmd.encode("ascii"):
        raise ValueError("native CLI rename echo mismatch — STOP (state uncertain)")
    # storage_cli_rename emits only an error line on failure.
    # shell emits CRLF before prompt even on successful no-output call.
    reply = client.read.until(client.CLI_PROMPT)
    if reply != b"\r\n":
        raise ValueError("native CLI rename reply ambiguous — STOP (state uncertain)")


def preflight(client, old_md5: str, new_md5: str,
              post: dict[str,str], js: dict[str,str]) -> None:
    client.send_and_wait_eol("device_info\r")
    identity = client.read.until(client.CLI_PROMPT)
    paths=dict(POST_REMOTE)
    paths.update({k:v for k,v in JS_REMOTE.items() if k not in paths})
    if set(paths.values()) != {
        APP_REMOTE, "/ext/apps_data/js_app/plugins/js_gpio.fal",
        "/ext/apps_data/js_app/plugins/js_event_loop.fal", "/ext/Manifest"
    }:
        raise ValueError("native resource scope changed")
    live={k:client.hash_flipper(p).strip() for k,p in paths.items()}
    check_resources(identity,{k:live[k] for k in POST_REMOTE},post)
    check_js(identity,{k:live[k] for k in JS_REMOTE},js)
    if stat(client,APP_REMOTE)!=OLD_SIZE:
        raise ValueError("installed original LabMate size changed")
    if stat(client,STAGE)!=NEW_SIZE_LINE:
        raise ValueError("staged final candidate not exact size")
    if stat(client,BACKUP)!=ABSENT:
        raise ValueError("reserved backup path already present")
    exact_md5(client,APP_REMOTE,old_md5)
    exact_md5(client,STAGE,new_md5)
    native_checks(client,post,js)


def promote_two_renames(client, post: dict[str,str], js: dict[str,str],
                        old_md5: str, new_md5: str) -> dict[str,str]:
    preflight(client,old_md5,new_md5,post,js)

    # First and second renames are NOT a single atomic transaction.
    # A disconnect here leaves app absent, but OLD app is safe at BACKUP.
    rename_once(client,APP_REMOTE,BACKUP)
    if stat(client,APP_REMOTE)!=ABSENT:
        raise ValueError("old active FAP did not disappear after rename; STOP")
    if stat(client,BACKUP)!=OLD_SIZE:
        raise ValueError("protected old-app on-device backup size mismatch; STOP")
    exact_md5(client,BACKUP,old_md5)
    if stat(client,STAGE)!=NEW_SIZE_LINE:
        raise ValueError("staged new FAP changed between rename phases; STOP")
    exact_md5(client,STAGE,new_md5)

    rename_once(client,STAGE,APP_REMOTE)
    if stat(client,APP_REMOTE)!=NEW_SIZE_LINE:
        raise ValueError("new active v1.8 FAP missing or wrong size after promotion; STOP")
    if stat(client,STAGE)!=ABSENT:
        raise ValueError("temporary stage still present after promotion; STOP")
    if stat(client,BACKUP)!=OLD_SIZE:
        raise ValueError("protected old E11 FAP missing after promotion; STOP")
    exact_md5(client,APP_REMOTE,new_md5)
    exact_md5(client,BACKUP,old_md5)
    native_checks(client,post,js)
    return {
        "result":"E11 FAP-ONLY PROMOTION FILE IDENTITY PASS",
        "active_fap":APP_REMOTE,
        "active_new_fap_md5":new_md5,
        "old_fap_device_backup":BACKUP,
        "old_fap_device_backup_md5":old_md5,
        "stage_now_absent":"YES",
        "native_js_manifest":"UNCHANGED",
        "firmware_flash":"NO",
        "user_csv_profiles":"NOT ACCESSED",
        "new_v18_app_boot_test":"PENDING",
        "stable_release":"NOT AUTHORIZED",
    }


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port",required=True)
    parser.add_argument("--momentum-scripts",required=True,type=Path)
    parser.add_argument("--old-candidate",required=True,type=Path)
    parser.add_argument("--saved-old-fap-backup",required=True,type=Path)
    parser.add_argument("--new-fap",required=True,type=Path)
    args=parser.parse_args()
    print("E11 PHASE 2B TWO SAME-DIRECTORY SAFE RENAMES (NOT FULL FIRMWARE FLASH)")
    print("INTERRUPTED 2B MAY TEMPORARILY REMOVE LABMATE FROM APP MENU.")
    print("ABSOLUTELY NO AUTO-RETRY OR AUTO-ROLLBACK IN FAILURE CASE.")
    try:
        if not re.fullmatch(r"COM[1-9][0-9]{0,2}",args.port):
            raise ValueError("invalid exact COMn port")
        blob=local_preflight(args.new_fap,args.saved_old_fap_backup,args.old_candidate)
        if hashlib.sha256(blob).hexdigest()!=NEW_FAP_SHA or len(blob)!=NEW_SIZE:
            raise ValueError("new FAP exact independent SHA/size lost")
        post,js=pinned_local_expectation(args.old_candidate)
        if hashlib.sha256((args.saved_old_fap_backup/
                "installed_E11_v18DEV_before_final_label.fap").read_bytes()).hexdigest()!=EXPECTED_SHA:
            raise ValueError("original PC FAP backup mismatch")
        import_path=args.momentum_scripts/"flipper"/"storage.py"
        if args.momentum_scripts.is_symlink() or import_path.is_symlink() or not import_path.is_file():
            raise ValueError("pinned Momentum CLI transport unavailable")
        sys.path.insert(0,str(args.momentum_scripts.resolve()))
        import flipper.storage as sdk
        verify_transport_origin(sdk.__file__,args.momentum_scripts)
        client=sdk.FlipperStorage(args.port)
        client.read=DeadlineRead(client.port,timeout_seconds=20)
        with client as live:
            result=promote_two_renames(live,post,js,post["E11_APP"],hashlib.md5(blob).hexdigest())
    except Exception as exc:
        cause=str(exc) if type(exc)==ValueError else type(exc).__name__
        print("E11 2B FAP-ONLY PROMOTION NO-GO: "+cause,file=sys.stderr)
        print("STOP — DO NOT RERUN, REMOVE, RENAME, FLASH OR AUTO-RESTORE.",file=sys.stderr)
        print("KEEP ORIGINAL PC FAP BACKUP; REQUEST READ-ONLY STATE RECONCILIATION.",file=sys.stderr)
        return 1
    for key,value in result.items():
        print(key+": "+value)
    print("E11 2B FAP-ONLY FILE PROMOTION PASS - v1.8 DEVICE GUI STILL PENDING")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
