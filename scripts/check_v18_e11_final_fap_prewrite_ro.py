#!/usr/bin/env python3
"""E11 v1.8 final FAP-only consent phase ONE: read-only device identity + PC backup.

NEVER uploads/writes an SD file, installs FAP, flashes/restores firmware, runs
JavaScript, opens an application, changes a GPIO mode or deletes old PC data.
Only CLI device_info, storage md5 and storage read_chunks of ONE exact
/ext/apps/Tools/labmate.fap. Writes a NEW PC-only backup folder after checks.

Consent to a later FAP replacement does not skip this fail-closed checkpoint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from check_v18_e11_postupdate_readonly import (
    REMOTE as POST_REMOTE, evaluate as compare_resource_identity,
    expected_md5 as packed_resource_md5,
)
from check_v18_e11_h_js_runtime_ro import (
    REMOTE as JS_REMOTE, compare_remote_identity as compare_js_identity,
    local_expected_md5 as packed_js_md5,
)
from preflight_v18_e11_local import ARTIFACTS

APP_REMOTE = "/ext/apps/Tools/labmate.fap"
EXPECTED_SHA = ARTIFACTS["labmate.fap"]
EXPECTED_BYTES = 81532
NEW_FAP_SHA = "393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61"
BACKUP_NAME = "installed_E11_v18DEV_before_final_label.fap"
MD5 = re.compile(r"[0-9a-fA-F]{32}\Z")


def safe_output(output: Path) -> None:
    if output.exists() or output.is_symlink():
        raise ValueError("PC backup output exists (refuse overwrite)")
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError("PC backup parent folder missing or linked")
    if output == output.parent or not output.is_absolute():
        raise ValueError("absolute new PC-only backup path required")


def pinned_local_expectation(old_candidate: Path) -> tuple[dict[str,str], dict[str,str]]:
    """Exact E11 FULL verified source/run + nested Manifest/event-loop hashes."""
    post = packed_resource_md5(old_candidate)
    js = packed_js_md5(old_candidate)
    if post["E11_APP"] != js["labmate.fap"] or post["E11_JS_GPIO"] != js["js_gpio.module"]:
        raise ValueError("independent pinned E11 resource app/JS identity disagree")
    local_app = old_candidate / "labmate.fap"
    if local_app.stat().st_size != EXPECTED_BYTES:
        raise ValueError("unexpected old E11 FAP byte count")
    return post, js


def check_and_copy(client, expected_post: dict[str,str], expected_js: dict[str,str],
                   destination: Path) -> dict[str,str]:
    """Caller has opened ONE trusted COM transport; everything on Flipper is read-only."""
    client.send_and_wait_eol("device_info\r")
    info=client.read.until(client.CLI_PROMPT)
    paths = dict(POST_REMOTE)
    paths.update({k: v for k,v in JS_REMOTE.items() if k not in paths})
    # Event loop MD5 included; only 4 fixed read-only remote paths accepted.
    if set(paths.values()) != {
        APP_REMOTE, "/ext/apps_data/js_app/plugins/js_gpio.fal",
        "/ext/apps_data/js_app/plugins/js_event_loop.fal", "/ext/Manifest"
    }:
        raise ValueError("remote resource read allowlist changed")
    first = {k:client.hash_flipper(path).strip() for k,path in paths.items()}
    p = {k:first[k] for k in POST_REMOTE}
    j = {k:first[k] for k in JS_REMOTE}
    compare_resource_identity(info,p,expected_post)
    compare_js_identity(info,j,expected_js)

    # Exactly one native FAP read from SD to memory; source file is never edited.
    content = client.read_file(APP_REMOTE)
    # PINNED Momentum storage.py / FlipperStorage.read_file() returns a
    # bytearray (not bytes) on a completed transfer. Only accept these
    # two exact binary containers; length and SHA256 independently
    # detect truncated serial reads from the upstream transport.
    if not isinstance(content, (bytes, bytearray)):
        raise ValueError("invalid nonbinary FAP readback")
    if len(content) != EXPECTED_BYTES:
        raise ValueError("incomplete/oversized FAP readback")
    content = bytes(content)
    if hashlib.sha256(content).hexdigest()!=EXPECTED_SHA:
        raise ValueError("readback FAP SHA256 differs from previously tested E11")
    if hashlib.md5(content).hexdigest()!=expected_post["E11_APP"]:
        raise ValueError("device FAP MD5/readback bytes disagree")
    second = {k:client.hash_flipper(path).strip() for k,path in paths.items()}
    if any(not MD5.fullmatch(second[k]) or second[k].lower()!=first[k].lower()
           for k in paths):
        raise ValueError("device resource identity changed during backup")

    # Only NOW create new PC backup; no existing folder/file may be overwritten.
    destination.mkdir(mode=0o700)
    incomplete=destination/"INCOMPLETE-DO-NOT-RESTORE.txt"
    incomplete.write_text("NOT VERIFIED; DO NOT DEPLOY, DELETE, OR RESTORE.\n",encoding="utf-8")
    fap=destination/BACKUP_NAME
    with fap.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    if fap.stat().st_size!=EXPECTED_BYTES or hashlib.sha256(fap.read_bytes()).hexdigest()!=EXPECTED_SHA:
        raise ValueError("PC FAP copy disk readback mismatch")
    report={
        "scope":"ONLY existing /ext/apps/Tools/labmate.fap copied to PC",
        "device_write":False, "firmware_flash":False,
        "target_candidate_fap_sha256":NEW_FAP_SHA,
        "installed_old_fap_sha256":EXPECTED_SHA,
        "installed_old_fap_bytes":EXPECTED_BYTES,
        "live_identity_fap_md5_verified_twice":True,
        "live_native_js_and_manifest_md5_verified_twice":True,
        "full_firmware_image_attested":False,
        "installation_performed":False,
        "stable_release_approved":False,
    }
    report_path=destination/"PREWRITE_READONLY_REPORT.json"
    with report_path.open("x",encoding="utf-8") as stream:
        json.dump(report,stream,indent=2,sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    (destination/"READ_ONLY_PC_FAP_BACKUP_VERIFIED.txt").write_text(
        "Exactly one live E11 FAP copied to PC with pinned SHA256 plus twice MD5 "
        "and unchanged native module/manifest identity. No device writes.\n",
        encoding="utf-8")
    incomplete.unlink()
    return {
        "backup_fap":str(fap),
        "old_fap_sha256":EXPECTED_SHA,
        "new_candidate_sha256_not_installed":NEW_FAP_SHA,
        "device_identity":"PINNED E11 LABEL/APP/JS/EVENT_LOOP/MANIFEST MATCH",
    }


def perform(port: str, scripts: Path, old_candidate: Path, destination: Path) -> dict[str,str]:
    if not re.fullmatch(r"COM[1-9][0-9]{0,2}",port):
        raise ValueError("exact COMn required")
    safe_output(destination)
    post,js=pinned_local_expectation(old_candidate)
    module = scripts/"flipper"/"storage.py"
    if scripts.is_symlink() or module.is_symlink() or not module.is_file():
        raise ValueError("trusted Momentum Flipper transport absent")
    sys.path.insert(0,str(scripts.resolve()))
    import flipper.storage as transport
    verify_transport_origin(transport.__file__,scripts)
    device=transport.FlipperStorage(port)
    device.read=DeadlineRead(device.port, timeout_seconds=25)
    with device as client:
        return check_and_copy(client,post,js,destination)


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port",required=True)
    p.add_argument("--momentum-scripts",type=Path,required=True)
    p.add_argument("--old-candidate",type=Path,required=True)
    p.add_argument("--pc-backup",type=Path,required=True)
    args=p.parse_args()
    print("E11 V1.8 FINAL PREWRITE: PINNED DEVICE IDENTITY + PC FAP BACKUP ONLY")
    print("NO INSTALL/FLASH/SD WRITE/APP RUN/RESET, AND NO AUTOMATIC RETRY.")
    try:
        output=perform(args.port,args.momentum_scripts,args.old_candidate,args.pc_backup)
    except Exception as exc:
        # Never echo raw device_info or private Flipper serial output.
        reason=str(exc) if type(exc)==ValueError else type(exc).__name__
        print("E11 FINAL PREWRITE NOT ACCEPTED: "+reason,file=sys.stderr)
        print("NO FAP UPLOAD AUTHORIZED FROM THIS OUTPUT. DO NOT RETRY BLINDLY.",file=sys.stderr)
        return 1
    print("E11 FINAL PREWRITE IDENTITY AND PC FAP BACKUP PASS - DEVICE READ ONLY")
    for key,value in output.items():
        print(key+": "+value)
    print("NEXT GATE: VERIFY FINAL CANDIDATE OFFLINE; REVIEW BEFORE ONE FAP WRITE.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
