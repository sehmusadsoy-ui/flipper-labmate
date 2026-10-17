#!/usr/bin/env python3
"""E11 v1.8 label phase 2A: stage new FAP as NON-app extension on Flipper.

One explicitly scoped device write: CREATE /ext/apps/Tools/labmate.e11-new-stage
only if absent. NEVER rename/remove/overwrite existing LabMate FAP,
never alter other apps, profiles, logs, native plugins, manifest, firmware.
Staged bytes verified MD5 + exact size; old app remains in place.
Do not launch or promote staged candidate from this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from check_v18_e11_final_fap_prewrite_ro import (
    APP_REMOTE, EXPECTED_BYTES, EXPECTED_SHA, NEW_FAP_SHA, BACKUP_NAME,
    pinned_local_expectation
)
from check_v18_e11_postupdate_readonly import REMOTE as POST_REMOTE, evaluate as compare_resources
from check_v18_e11_h_js_runtime_ro import REMOTE as JS_REMOTE, compare_remote_identity as compare_js

STAGE = "/ext/apps/Tools/labmate.e11-new-stage"
OLD_BACKUP_TARGET = "/ext/apps/Tools/labmate.e11-pre-final.bak"
NEW_SIZE = 81528
BUF = 4096
REPORT = "PREWRITE_READONLY_REPORT.json"
MARKER = "READ_ONLY_PC_FAP_BACKUP_VERIFIED.txt"
MISSING = b"Storage error: file/dir not exist"
MD5 = re.compile(r"[0-9a-fA-F]{32}\Z")


def sha(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError("required regular PC input missing")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def local_preflight(new_fap: Path, backup: Path, original: Path) -> bytes:
    if backup.is_symlink() or not backup.is_dir():
        raise ValueError("actual old-app PC backup directory missing")
    if original.is_symlink() or not original.is_dir():
        raise ValueError("pinned original trial E11 FULL archive missing")
    if backup.resolve() == original.resolve() or original.resolve() in backup.resolve().parents:
        raise ValueError("old-app backup cannot reside in source artifact folder")
    expected_files={BACKUP_NAME, REPORT, MARKER}
    if {p.name for p in backup.iterdir()} != expected_files:
        raise ValueError("PC actual old-app backup inventory changed")
    for p in backup.iterdir():
        if p.is_symlink() or not p.is_file():
            raise ValueError("unsafe backup file")
    old=backup/BACKUP_NAME
    if old.stat().st_size != EXPECTED_BYTES or sha(old) != EXPECTED_SHA:
        raise ValueError("old FAP saved from device not exact E11")
    record=json.loads((backup/REPORT).read_text("utf-8"))
    mandatory={
        "scope":"ONLY existing /ext/apps/Tools/labmate.fap copied to PC",
        "device_write":False, "firmware_flash":False,
        "target_candidate_fap_sha256":NEW_FAP_SHA,
        "installed_old_fap_sha256":EXPECTED_SHA,
        "installed_old_fap_bytes":EXPECTED_BYTES,
        "live_identity_fap_md5_verified_twice":True,
        "live_native_js_and_manifest_md5_verified_twice":True,
        "installation_performed":False,
        "stable_release_approved":False,
    }
    if not isinstance(record,dict) or any(record.get(k)!=v for k,v in mandatory.items()):
        raise ValueError("prewrite report changed / was not actual PASS")
    if not (backup/MARKER).stat().st_size:
        raise ValueError("verified PC backup completion marker missing")
    if sha(new_fap)!=NEW_FAP_SHA or new_fap.stat().st_size!=NEW_SIZE:
        raise ValueError("new review-only FAP bytes differ from independently pinned CI")
    if new_fap.resolve() == old.resolve():
        raise ValueError("new candidate and preserved old PC app cannot share a path")
    return new_fap.read_bytes()


def checked_stat(client, path: str) -> bytes:
    if path not in (APP_REMOTE, STAGE, OLD_BACKUP_TARGET):
        raise ValueError("unapproved Flipper SD stat")
    client.send_and_wait_eol(f'storage stat "{path}"\r')
    raw=client.read.until(client.CLI_EOL)
    tail=client.read.until(client.CLI_PROMPT)
    if tail.strip():
        raise ValueError("unexpected Flipper SD stat framing")
    return raw


def check_absent(client, path: str) -> None:
    result=checked_stat(client,path)
    if result != MISSING:
        raise ValueError("reserved stage or old-FAP backup path already exists / ambiguous")


def check_old_and_native(client, post: dict[str,str], js: dict[str,str]) -> None:
    client.send_and_wait_eol("device_info\r")
    info=client.read.until(client.CLI_PROMPT)
    paths=dict(POST_REMOTE)
    paths.update({k:v for k,v in JS_REMOTE.items() if k not in paths})
    if set(paths.values()) != {
        APP_REMOTE,"/ext/apps_data/js_app/plugins/js_gpio.fal",
        "/ext/apps_data/js_app/plugins/js_event_loop.fal","/ext/Manifest"
    }:
        raise ValueError("fixed read-only resource allowlist modified")
    remote={k:client.hash_flipper(p).strip() for k,p in paths.items()}
    compare_resources(info,{k:remote[k] for k in POST_REMOTE},post)
    compare_js(info,{k:remote[k] for k in JS_REMOTE},js)
    if checked_stat(client,APP_REMOTE) != b"File, size: 81532b":
        raise ValueError("installed old FAP size changed from accepted E11")
    check_absent(client,STAGE)
    check_absent(client,OLD_BACKUP_TARGET)


def append_staged_chunk(client, blob: bytes) -> None:
    if not 1<=len(blob)<=BUF:
        raise ValueError("unsafe stage byte count")
    # Upstream Momentum storage write_chunk is FSOM_OPEN_APPEND; NEVER target
    # the installed FAP. Filename fixed to initially nonexistent staging.
    # PINNED Momentum native cli_shell_line_input_normal() echoes EACH
    # printable command byte. cli_shell_line_input_cr() then prints CRLF
    # BEFORE executing storage_cli_write_chunk(), which emits Ready+CRLF.
    # FlipperStorage.send_and_wait_eol() consumes and RETURNS the echoed
    # command line, not Ready. Therefore require BOTH exact lines before
    # sending any binary bytes; do not guess or discard unknown lines.
    command=f'storage write_chunk "{STAGE}" {len(blob)}'
    echo=client.send_and_wait_eol(command+"\r")
    if echo!=command.encode("ascii"):
        raise ValueError("unexpected echoed CLI command; STOP before payload")
    ready=client.read.until(client.CLI_EOL)
    if ready!=b"Ready":
        raise ValueError("expected exact second-line Ready; STOP before payload")
    count=client.port.write(blob)
    if count!=len(blob):
        raise ValueError("USB stage write incomplete: STOP; no automatic retry")
    client.port.flush()
    end=client.read.until(client.CLI_PROMPT)
    if end.strip():
        raise ValueError("unexpected stage write reply: STOP; do not auto retry")


def stage_one_file(client, blob: bytes, post: dict[str,str], js: dict[str,str]) -> dict[str,str]:
    if not isinstance(blob,bytes) or len(blob)!=NEW_SIZE or hashlib.sha256(blob).hexdigest()!=NEW_FAP_SHA:
        raise ValueError("refuse unknown target candidate")
    # Stage only AFTER all source, live identity and absence checks have passed.
    check_old_and_native(client,post,js)
    for offset in range(0,len(blob),BUF):
        append_staged_chunk(client,blob[offset:offset+BUF])
    if checked_stat(client,STAGE)!=b"File, size: 81528b":
        raise ValueError("new staging file size disagrees; STOP NO RETRY")
    expected_md5=hashlib.md5(blob).hexdigest()
    actual_stage=client.hash_flipper(STAGE).strip()
    if not MD5.fullmatch(actual_stage) or actual_stage.lower()!=expected_md5:
        raise ValueError("Flipper staged FAP MD5 mismatch; STOP NO RETRY")
    # Do not re-run absent-stage audit: stage now intentionally exists.
    # Old original application must still be installed with matching MD5.
    if client.hash_flipper(APP_REMOTE).strip().lower()!=post["E11_APP"]:
        raise ValueError("original live app unexpectedly changed; STOP")
    if checked_stat(client,APP_REMOTE)!=b"File, size: 81532b":
        raise ValueError("original live app size changed; STOP")
    for key,path in JS_REMOTE.items():
        if key == "labmate.fap":
            continue
        if client.hash_flipper(path).strip().lower()!=js[key]:
            raise ValueError("native JS resource changed during stage; STOP")
    if client.hash_flipper("/ext/Manifest").strip().lower()!=post["E11_NEW_MANIFEST"]:
        raise ValueError("Manifest changed during stage; STOP")
    check_absent(client,OLD_BACKUP_TARGET)
    return {
        "result":"E11 FINAL STAGED FAP MD5 PASS - ORIGINAL LABMATE UNCHANGED",
        "new_stage_path":STAGE,
        "new_fap_sha256_pc":NEW_FAP_SHA,
        "new_fap_md5_device":expected_md5,
        "old_fap_sha256_pc_backup":EXPECTED_SHA,
        "old_active_app_still_installed":"YES",
        "new_stage_is_active_app":"NO",
        "firmware_or_user_data_write":"NO",
        "final_swap_performed":"NO",
    }


def perform(port: str,transport: Path, original: Path, backup: Path, new_fap: Path) -> dict[str,str]:
    if not re.fullmatch(r"COM[1-9][0-9]{0,2}",port):
        raise ValueError("explicit COMn required")
    blob=local_preflight(new_fap,backup,original)
    post,js=pinned_local_expectation(original)
    module=transport/"flipper"/"storage.py"
    if transport.is_symlink() or module.is_symlink() or not module.is_file():
        raise ValueError("pinned Momentum serial transport unavailable")
    sys.path.insert(0,str(transport.resolve()))
    import flipper.storage as sdk
    verify_transport_origin(sdk.__file__,transport)
    cli=sdk.FlipperStorage(port)
    cli.read=DeadlineRead(cli.port,timeout_seconds=20)
    cli.port.write_timeout=12
    with cli as connected:
        return stage_one_file(connected,blob,post,js)


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port",required=True)
    p.add_argument("--momentum-scripts",type=Path,required=True)
    p.add_argument("--old-candidate",type=Path,required=True)
    p.add_argument("--saved-old-fap-backup",type=Path,required=True)
    p.add_argument("--new-fap",type=Path,required=True)
    args=p.parse_args()
    print("E11 FINAL ONE-FAP STAGE: creates ONLY one non-app .e11-new-stage sidecar.")
    print("SOURCE APP PRESERVED. NO FIRMWARE, MANIFEST, JS, USER DATA WRITE.")
    print("IMPORTANT: on error STOP; never blindly retry or delete stage.")
    try:
        info=perform(args.port,args.momentum_scripts,args.old_candidate,
                     args.saved_old_fap_backup,args.new_fap)
    except Exception as exc:
        reason=str(exc) if type(exc)==ValueError else type(exc).__name__
        print("E11 FINAL ONE-FAP STAGE NO-GO: "+reason,file=sys.stderr)
        print("STOP; DO NOT CLEAN UP/RETRY, DO NOT RENAME OLD APP.",file=sys.stderr)
        return 1
    for k,v in info.items():
        print(k+": "+v)
    print("E11 FINAL ONE-FAP STAGE PASS - FINAL APP RENAME NOT EXECUTED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
