#!/usr/bin/env python3
"""READ ONLY after/before E11 phase 2B safe two-rename v1.8 FAP promotion.

Classify and attest ONLY three fixed on-SD file paths:
 BEFORE: original installed, final sidecar staged, no on-device backup
 BETWEEN: original safely backed up, stage still present, app path absent
 AFTER: final installed, original backed up, stage absent

Any unknown/mismatched path, file bytes, resource MD5 or firmware label/base
is NO-GO and cannot silently trigger retry, delete, rename, restore or flash.
The instrument does not access CSV/Profiles/other apps or write to Flipper.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from check_v18_e11_final_fap_prewrite_ro import pinned_local_expectation, APP_REMOTE, EXPECTED_SHA
from check_v18_e11_postupdate_readonly import (
    REMOTE as POST_REMOTE, EXPECTED_BASE, EXPECTED_FIRMWARE_LABEL
)
from check_v18_e11_h_js_runtime_ro import REMOTE as JS_REMOTE
from stage_v18_final_fap_on_device_one_file import (
    STAGE,OLD_BACKUP_TARGET as BACKUP,NEW_SIZE,local_preflight
)

ABSENT=b"Storage error: file/dir not exist"
OLD_LINE=b"File, size: 81532b"
NEW_LINE=b"File, size: 81528b"
ALLOW={APP_REMOTE,STAGE,BACKUP}
STATUS={
    (OLD_LINE,NEW_LINE,ABSENT):"BEFORE_PROMOTION",
    (ABSENT,NEW_LINE,OLD_LINE):"BETWEEN_TWO_RENAMES",
    (NEW_LINE,ABSENT,OLD_LINE):"AFTER_PROMOTION",
}

def stat_exact(client,path: str) -> bytes:
    if path not in ALLOW:
        raise ValueError("unapproved E11 status path")
    cmd=f'storage stat "{path}"'
    echo=client.send_and_wait_eol(cmd+"\r")
    if echo!=cmd.encode("ascii"):
        raise ValueError("unrecognized read-only CLI echo")
    data=client.read.until(client.CLI_EOL)
    tail=client.read.until(client.CLI_PROMPT)
    if tail!=b"\r\n" or data not in (ABSENT,OLD_LINE,NEW_LINE):
        raise ValueError("unrecognized file status framing")
    return data

def md5_exact(client,path: str,expected: str) -> None:
    allowed=ALLOW|{"/ext/apps_data/js_app/plugins/js_gpio.fal",
                   "/ext/apps_data/js_app/plugins/js_event_loop.fal","/ext/Manifest"}
    if path not in allowed:
        raise ValueError("unapproved resource MD5 query")
    actual=client.hash_flipper(path).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{32}",actual) or actual!=expected:
        raise ValueError("resource size-independent hash mismatch at allowed path "+path)

def audit(client,post: dict[str,str],js: dict[str,str],
          old_digest: str,new_digest: str) -> dict[str,str]:
    # Note: independent pinned resource checks from source do NOT depend
    # on active FAP MD5 as it legitimately changes between rename states.
    client.send_and_wait_eol("device_info\r")
    ident=client.read.until(client.CLI_PROMPT)
    if not isinstance(ident,bytes) or not 1<=len(ident)<=131072:
        raise ValueError("unrecognized firmware identity")
    lower=ident.decode("utf-8",errors="strict").lower()
    if EXPECTED_FIRMWARE_LABEL not in lower or EXPECTED_BASE not in lower:
        raise ValueError("live firmware identity/base drift")
    for name,path in JS_REMOTE.items():
        if path!=APP_REMOTE:
            md5_exact(client,path,js[name])
    md5_exact(client,"/ext/Manifest",post["E11_NEW_MANIFEST"])
    statuses=tuple(stat_exact(client,path) for path in (APP_REMOTE,STAGE,BACKUP))
    state=STATUS.get(statuses)
    if state is None:
        raise ValueError("FAP state not one of three explicitly expected patterns")
    if statuses[0]!=ABSENT:
        md5_exact(client,APP_REMOTE,old_digest if state=="BEFORE_PROMOTION" else new_digest)
    if statuses[1]!=ABSENT:
        md5_exact(client,STAGE,new_digest)
    if statuses[2]!=ABSENT:
        md5_exact(client,BACKUP,old_digest)
    # Revalidate all 3 statuses AFTER remote MD5 to detect movement during audit
    if tuple(stat_exact(client,path) for path in (APP_REMOTE,STAGE,BACKUP))!=statuses:
        raise ValueError("FAP files moved during read-only state check")
    return {
       "state":state,
       "old_E11_FAP_preserved":(
           "PC_BACKUP_AND_ACTIVE" if state=="BEFORE_PROMOTION" else
           "PC_BACKUP_AND_DEVICE_BAK"
       ),
       "new_v18_FAP":(
           "STAGED_NOT_ACTIVE" if state!="AFTER_PROMOTION" else "ACTIVE_MD5_AND_SIZE_PASS"
       ),
       "firmware_JS_gpio_eventloop_manifest":"PINNED_MD5_AND_LABEL_MATCH",
       "device_writes":"NONE",
       "automatic_rollback_or_retry":"NO",
       "gui_v18_device_run":"NOT_TESTED",
    }

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port",required=True)
    p.add_argument("--momentum-scripts",required=True,type=Path)
    p.add_argument("--old-candidate",required=True,type=Path)
    p.add_argument("--saved-old-fap-backup",required=True,type=Path)
    p.add_argument("--new-fap",required=True,type=Path)
    args=p.parse_args()
    print("E11 PHASE 2B STATE RECONCILIATION - STRICT READ ONLY")
    try:
        if not re.fullmatch(r"COM[1-9][0-9]{0,2}",args.port):
            raise ValueError("explicit COM port required")
        candidate=local_preflight(args.new_fap,args.saved_old_fap_backup,args.old_candidate)
        post,js=pinned_local_expectation(args.old_candidate)
        if hashlib.sha256((args.saved_old_fap_backup/
                "installed_E11_v18DEV_before_final_label.fap").read_bytes()).hexdigest()!=EXPECTED_SHA:
            raise ValueError("original PC saved app backup changed")
        new_md5=hashlib.md5(candidate).hexdigest()
        source=args.momentum_scripts
        library=source/"flipper"/"storage.py"
        if source.is_symlink() or library.is_symlink() or not library.is_file():
            raise ValueError("pinned Momentum CLI scripts missing")
        sys.path.insert(0,str(source.resolve()))
        import flipper.storage as storage
        verify_transport_origin(storage.__file__,source)
        cli=storage.FlipperStorage(args.port)
        cli.read=DeadlineRead(cli.port,timeout_seconds=20)
        with cli as connected:
            result=audit(connected,post,js,post["E11_APP"],new_md5)
    except Exception as exc:
        reason=str(exc) if type(exc)==ValueError else type(exc).__name__
        print("E11 PHASE 2B STATE READ-ONLY NO-GO: "+reason,file=sys.stderr)
        print("STOP; do NOT retry, clean, rename, flash or launch a mismatched FAP.",file=sys.stderr)
        return 1
    for k,v in result.items():print(k+": "+v)
    print("E11 PHASE 2B READ-ONLY STATE VERIFIED; NO DEVICE WRITE")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
