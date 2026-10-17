#!/usr/bin/env python3
"""Stage ONLY verified new v1.8 label FAP on PC using real E11 backup.

NO DEVICE, NO SERIAL, NO UPLOADER, NO INSTALL, NO REBOOT and NO
microSD writes. Fail-closed exact GitHub archived candidate verification.
Create a NEW local output directory outside both inputs; no overwrite.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from verify_v18_full_review_pair import verify

FINAL_SOURCE = "99cb65d0194dc59d423cfa439c90618ac6b9f114"
FINAL_RUN = 39035056937
EXPECTED = {
    "labmate.fap": "393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61",
    "firmware.dfu": "e7460ab56d72a77bca1c096496ee6dd6d59044bd314ad4cb78559c3aeff72c8b",
    "js_gpio.module": "fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a",
    "firmware-full-update.tgz": "cd12be2a85512dcd360e6b93e027fa2ad9136a76602ba01036dc235b7a804dee",
}
OLD_SHA = "2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0"
OLD_BYTES = 81532
NEW_BYTES = 81528
OLD_NAME = "installed_E11_v18DEV_before_final_label.fap"
REPORT_NAME = "PREWRITE_READONLY_REPORT.json"
MARKER_NAME = "READ_ONLY_PC_FAP_BACKUP_VERIFIED.txt"
OUTPUT_FAP = "labmate_v18_FINAL_REVIEW_PC_ONLY.fap"


def insist(test: bool, detail: str) -> None:
    if not test:
        raise ValueError(detail)


def sha256(path: Path) -> str:
    insist(path.is_file() and not path.is_symlink(), "missing or linked input file")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_within(child: Path, parent: Path) -> bool:
    return child == parent or parent in child.parents


def examine(candidate: Path, backup: Path, output: Path) -> dict[str, object]:
    insist(candidate.is_dir() and not candidate.is_symlink(), "candidate directory unavailable")
    insist(backup.is_dir() and not backup.is_symlink(), "prewrite PC backup directory unavailable")
    insist(not output.exists() and not output.is_symlink(), "output exists: never overwrite")
    insist(output.parent.is_dir() and not output.parent.is_symlink(), "output PC parent missing")
    c = candidate.resolve(strict=True)
    b = backup.resolve(strict=True)
    o = output.resolve(strict=False)
    insist(c != b and not is_within(o,c) and not is_within(o,b),
           "output would modify candidate or installed PC backup")
    insist(not is_within(c,o) and not is_within(b,o),
           "output contains protected candidate or PC backup")
    insist(not is_within(c,b) and not is_within(b,c),
           "candidate and backup overlap")

    for name, expected in EXPECTED.items():
        p = candidate / name
        insist(sha256(p) == expected, "candidate pinned SHA256 mismatch: " + name)
    # Heavy audit covers package seven-file inventory, exact source/run,
    # E11 native firmware ABI patches, updater and resource provenance.
    verify(candidate, FINAL_SOURCE, FINAL_RUN)

    expected_files = {OLD_NAME, REPORT_NAME, MARKER_NAME}
    found = list(backup.iterdir())
    insist(len(found) == len(expected_files) and
           {p.name for p in found} == expected_files,
           "PC backup folder has missing/extra files")
    for file in found:
        insist(file.is_file() and not file.is_symlink(), "PC backup is not regular files")
    old = backup / OLD_NAME
    insist(old.stat().st_size == OLD_BYTES and sha256(old) == OLD_SHA,
           "actual previously installed v1.8DEV FAP backup mismatch")
    report = json.loads((backup / REPORT_NAME).read_text("utf-8"))
    insist(isinstance(report, dict) and
           report.get("scope") == "ONLY existing /ext/apps/Tools/labmate.fap copied to PC" and
           report.get("device_write") is False and
           report.get("firmware_flash") is False and
           report.get("live_identity_fap_md5_verified_twice") is True and
           report.get("live_native_js_and_manifest_md5_verified_twice") is True and
           report.get("installation_performed") is False and
           report.get("stable_release_approved") is False and
           report.get("installed_old_fap_sha256") == OLD_SHA and
           report.get("installed_old_fap_bytes") == OLD_BYTES and
           report.get("target_candidate_fap_sha256") == EXPECTED["labmate.fap"],
           "prewrite PC FAP report provenance or read-only status differs")
    insist((backup / MARKER_NAME).stat().st_size > 0,
           "PC backup lacks verified marker")
    insist((candidate/"labmate.fap").stat().st_size == NEW_BYTES,
           "new label FAP size changed")
    return {
        "original_fap_sha256": OLD_SHA,
        "original_fap_bytes": OLD_BYTES,
        "final_candidate_fap_sha256": EXPECTED["labmate.fap"],
        "final_candidate_fap_bytes": NEW_BYTES,
        "original_fap_is_preserved": True,
        "firmware_was_not_flushed_or_installed": True,
        "device_write": False,
        "review_candidate_source": FINAL_SOURCE,
        "review_candidate_actions_run": FINAL_RUN,
        "publication_authorized": False,
    }


def stage(candidate: Path, backup: Path, output: Path) -> dict[str, object]:
    result = examine(candidate, backup, output)
    output.mkdir(mode=0o700)
    incomplete = output/"INCOMPLETE-NOT-FOR-DEVICE.txt"
    incomplete.write_text("NOT VERIFIED: DO NOT INSTALL, COPY TO FLIPPER, OR RELEASE.\n",encoding="utf-8")
    destination = output/OUTPUT_FAP
    blob = (candidate/"labmate.fap").read_bytes()
    with destination.open("xb") as stream:
        stream.write(blob)
        stream.flush()
        os.fsync(stream.fileno())
    insist(destination.stat().st_size == NEW_BYTES and sha256(destination) == EXPECTED["labmate.fap"],
           "PC staged final FAP disk readback mismatch")
    report = output/"FINAL_LABEL_FAP_PC_ONLY_AUDIT.json"
    with report.open("x",encoding="utf-8") as stream:
        json.dump(result,stream,indent=2,sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    (output/"VERIFIED_PC_ONLY_DO_NOT_INSTALL.txt").write_text(
        "Candidate LabMate v1.8 label FAP exact SHA256 verified against independent"
        " GitHub Actions review artifact, old installed FAP PC backup verified."
        " NO Flipper SD write, NO release, NO automatic transfer.\n",
        encoding="utf-8")
    incomplete.unlink()
    return result


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate",type=Path,required=True)
    parser.add_argument("--old-fap-backup",type=Path,required=True)
    parser.add_argument("--pc-output",type=Path,required=True)
    args=parser.parse_args()
    print("E11 FINAL v1.8 LABEL FAP - PC-ONLY ORIGINAL BACKUP + REVIEW PAIR VALIDATOR")
    try:
        report=stage(args.candidate,args.old_fap_backup,args.pc_output)
    except Exception as error:
        message=str(error) if type(error)==ValueError else type(error).__name__
        print("E11 FINAL PC-ONLY STAGING BLOCKED: "+message,file=sys.stderr)
        print("NO FLASH, NO INSTALL, NO DEVICE WRITE. DO NOT BYPASS.",file=sys.stderr)
        return 1
    print("E11 EXACT ORIGINAL FAP PC BACKUP: PASS")
    print("E11 FINAL REVIEW PAIR SOURCE/RUN/FAP/PLUGIN/UPDATER: PASS")
    print("E11 FINAL LABEL FAP PC-ONLY STAGING PASS - NO DEVICE OPERATION")
    for key,value in report.items():
        print(key+": "+str(value))
    print("NEXT: REVIEW STAGED SHA AND DEVICE ONE-FAP SAFE TRANSACTION METHOD")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
