#!/usr/bin/env python3
"""E11 v1.9 prospective app-trial DEVICE PREWRITE READ-ONLY SCREEN.

Unlike v1.8's stage/promotion scripts, this script has NO write/upload/rename
path at all. Only uses Flipper CLI device_info, storage stat, storage md5.
It verifies active v1.8 and preserved native resources twice while requiring
TWO *new* v1.9 candidate/rollback filenames to be ABSENT. Absent is a
precondition, NOT device-write authorization or firmware-image attestation.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from backup_v19_active_v18_fap_ro import check_local
from check_v18_e11_phase2b_state_readonly import audit, ABSENT
from prepare_v19_e11_pc_only import verify_backups

PROPOSED_STAGE = "/ext/apps/Tools/labmate.v19-new-stage"
PROPOSED_FINAL_V18_BACKUP = "/ext/apps/Tools/labmate.v18-final-before-v19.bak"
RESERVED = frozenset((PROPOSED_STAGE, PROPOSED_FINAL_V18_BACKUP))
EXPECTED_STATE = "AFTER_PROMOTION"


def stat_reserved_absent(client, path: str) -> None:
    """Reject anything except EXACT CLI command echo, ABSENT status and prompt."""
    if path not in RESERVED:
        raise ValueError("unapproved device CLI pathname")
    if client.CLI_EOL != "\r\n" or client.CLI_PROMPT != ">: ":
        raise ValueError("unrecognized pinned native serial framing")
    command = f'storage stat "{path}"'
    echo = client.send_and_wait_eol(command + "\r")
    if echo != command.encode("ascii"):
        raise ValueError("unexpected CLI command echo for reserved path")
    status = client.read.until(client.CLI_EOL)
    trail = client.read.until(client.CLI_PROMPT)
    if trail != b"\r\n" or status != ABSENT:
        raise ValueError("v1.9 reserved on-device path already exists or is ambiguous")


def attest_current_v18_and_free_names(client, post: dict, js: dict, v18_md5: str) -> dict:
    """The device is unmodified. A live drift or any sidecar blocks progress."""
    initial = audit(client, post, js, post["E11_APP"], v18_md5)
    if initial.get("state") != EXPECTED_STATE:
        raise ValueError("active app not previously verified final v1.8")
    if initial.get("new_v18_FAP") != "ACTIVE_MD5_AND_SIZE_PASS":
        raise ValueError("active final v1.8 FAP MD5 or size mismatch")
    if initial.get("old_E11_FAP_preserved") != "PC_BACKUP_AND_DEVICE_BAK":
        raise ValueError("historical original E11 FAP/device backup mismatch")
    if initial.get("firmware_JS_gpio_eventloop_manifest") != "PINNED_MD5_AND_LABEL_MATCH":
        raise ValueError("native E11 resource identity mismatch")
    for name in sorted(RESERVED):
        stat_reserved_absent(client, name)
    final = audit(client, post, js, post["E11_APP"], v18_md5)
    if final != initial:
        raise ValueError("active v1.8 or E11 native resources drifted during preflight")
    for name in sorted(RESERVED):
        stat_reserved_absent(client, name)
    return {
        "device_firmware_identity": "PINNED_E11_LABEL_BASE_AND_RESOURCE_MD5",
        "active_app": "V18_FINAL_MD5_SIZE_PASS",
        "prior_v18dev_device_backup": "PINNED_MD5_PASS",
        "v19_reserved_paths": "BOTH_ABSENT_TWICE",
        "old_e11_backup_preserved": "YES",
        "device_writes": "NONE",
        "v19_installed": "NO",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--momentum-scripts", required=True, type=Path)
    parser.add_argument("--old-candidate", required=True, type=Path)
    parser.add_argument("--saved-old-fap-backup", required=True, type=Path)
    parser.add_argument("--final-v18-fap", required=True, type=Path)
    parser.add_argument("--active-v18-backup", required=True, type=Path)
    parser.add_argument("--data-snapshot", required=True, type=Path)
    args = parser.parse_args()
    print("V19 E11 FIRST TRIAL DEVICE PREWRITE: READ ONLY, NO INSTALL/FLASH")
    try:
        if not re.fullmatch(r"COM[1-9][0-9]{0,2}", args.port):
            raise ValueError("explicit trusted COM port required")

        # All PC backup/snapshot evidence is rehashed first; FAIL BEFORE
        # serial open if any immutable recovery file is altered or missing.
        snapshot_count, snapshot_bytes = verify_backups(
            args.active_v18_backup, args.saved_old_fap_backup, args.data_snapshot
        )
        post, js, final_md5 = check_local(
            args.final_v18_fap, args.saved_old_fap_backup, args.old_candidate
        )
        scripts = args.momentum_scripts
        transport_file = scripts / "flipper" / "storage.py"
        if scripts.is_symlink() or not transport_file.is_file() or transport_file.is_symlink():
            raise ValueError("pinned transport missing or symlink")
        sys.path.insert(0, str(scripts.resolve()))
        import flipper.storage as transport
        verify_transport_origin(transport.__file__, scripts)
        device = transport.FlipperStorage(args.port)
        device.read = DeadlineRead(device.port, timeout_seconds=25)
        with device as client:
            result = attest_current_v18_and_free_names(client, post, js, final_md5)
    except Exception as exc:
        cause = str(exc) if type(exc) is ValueError else type(exc).__name__
        print("V19 E11 DEVICE PREWRITE READ-ONLY NO-GO: " + cause, file=sys.stderr)
        print("STOP: do not retry, upload, delete, rename, reset or flash.", file=sys.stderr)
        return 1

    for name, value in result.items():
        print(name + ": " + value)
    print(f"PC_LABMATE_DATA_BACKUP: VERIFIED ({snapshot_count} files, {snapshot_bytes} bytes)")
    print("V19 E11 DEVICE PREWRITE READ-ONLY PASS")
    print("NO DEVICE WRITES. INSTALL STILL REQUIRES NEW EXPLICIT CONSENT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
