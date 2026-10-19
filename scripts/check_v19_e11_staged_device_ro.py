#!/usr/bin/env python3
"""Independent v1.9 E11 POST-STAGE read-only Flipper file-state attestation.

Device operations are limited to existing Momentum CLI device_info,
storage stat, storage md5, and storage read_chunks. This source contains NO
write/upload, rename, remove, firmware flash, resource operation or rollback.
Verifies 2 FULL independent readbacks of 97,540-byte stage bytes; confirms
active final v1.8 and earlier E11 backup remain exact, and future v1.8
recovery filename is still absent.

Only invoke on the existing stage state; do NOT run old prewrite checker.
A device query failure is NO-GO and NEVER licenses automatic repair.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys
import argparse

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from backup_v19_active_v18_fap_ro import check_local
from check_v18_e11_phase2b_state_readonly import audit, ABSENT
from prepare_v19_e11_pc_only import FAP_BYTES, FAP_SHA, verify_backups

STAGE = "/ext/apps/Tools/labmate.v19-new-stage"
RECOVERY = "/ext/apps/Tools/labmate.v18-final-before-v19.bak"
ALLOWED = frozenset((STAGE, RECOVERY))
REMOTE_SIZE = f"File, size: {FAP_BYTES}b".encode("ascii")
HEX_MD5 = re.compile(r"[0-9a-f]{32}\Z")


def verified_candidate(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size != FAP_BYTES:
        raise ValueError("missing/unsafe/wrong-sized Windows PC v1.9 FAP")
    data = path.read_bytes()
    if len(data) != FAP_BYTES or hashlib.sha256(data).hexdigest() != FAP_SHA:
        raise ValueError("Windows PC candidate v1.9 SHA256 mismatch")
    return data


def stat_exact(client, path: str) -> bytes:
    if path not in ALLOWED:
        raise ValueError("forbidden post-stage status path")
    if client.CLI_EOL != "\r\n" or client.CLI_PROMPT != ">: ":
        raise ValueError("unrecognized native E11 CLI framing")
    cmd = f'storage stat "{path}"'
    echoed = client.send_and_wait_eol(cmd + "\r")
    if echoed != cmd.encode("ascii"):
        raise ValueError("post-stage stat CLI echo mismatch")
    status = client.read.until(client.CLI_EOL)
    tail = client.read.until(client.CLI_PROMPT)
    if tail != b"\r\n" or status not in (ABSENT, REMOTE_SIZE):
        raise ValueError("unrecognized post-stage status response")
    return status


def stage_full_readback(client, expected: bytes) -> None:
    if stat_exact(client, STAGE) != REMOTE_SIZE:
        raise ValueError("expected v1.9 staged sidecar not exactly present")
    found = client.hash_flipper(STAGE)
    if not isinstance(found, str):
        raise ValueError("staged device MD5 not text")
    found = found.strip().lower()
    if HEX_MD5.fullmatch(found) is None or found != hashlib.md5(expected).hexdigest():
        raise ValueError("staged device sidecar MD5 mismatch")
    actual = client.read_file(STAGE)
    if not isinstance(actual, (bytes, bytearray)):
        raise ValueError("full staged file is not binary")
    actual = bytes(actual)
    if (len(actual) != FAP_BYTES or
            hashlib.sha256(actual).hexdigest() != FAP_SHA or actual != expected):
        raise ValueError("full staged file SHA256 / binary readback mismatch")
    if client.hash_flipper(STAGE).strip().lower() != found:
        raise ValueError("stage file changed while being read")
    if stat_exact(client, STAGE) != REMOTE_SIZE:
        raise ValueError("stage size drifted during readback")


def attest_poststage(client, post: dict, js: dict, v18_md5: str,
                     candidate: bytes) -> dict:
    if (type(candidate) is not bytes or len(candidate) != FAP_BYTES or
            hashlib.sha256(candidate).hexdigest() != FAP_SHA):
        raise ValueError("incorrect local v1.9 FAP content")
    audits = []
    for _ in range(3):
        now = audit(client, post, js, post["E11_APP"], v18_md5)
        if (now.get("state") != "AFTER_PROMOTION" or
                now.get("new_v18_FAP") != "ACTIVE_MD5_AND_SIZE_PASS" or
                now.get("old_E11_FAP_preserved") != "PC_BACKUP_AND_DEVICE_BAK" or
                now.get("firmware_JS_gpio_eventloop_manifest") !=
                "PINNED_MD5_AND_LABEL_MATCH"):
            raise ValueError("installed final v1.8, old E11 backup or resource drift")
        audits.append(now)
        if stat_exact(client, RECOVERY) != ABSENT:
            raise ValueError("future v1.8 recovery name unexpectedly occupied")
        if len(audits) < 3:
            stage_full_readback(client, candidate)
    if audits[0] != audits[1] or audits[1] != audits[2]:
        raise ValueError("native installed v1.8/E11 identity changed across audit")
    if stat_exact(client, RECOVERY) != ABSENT:
        raise ValueError("new recovery name changed after device readback")
    if stat_exact(client, STAGE) != REMOTE_SIZE:
        raise ValueError("staged v1.9 FAP vanished or changed at final check")
    return {
        "state": "STAGED_V19_NONAPP_ACTIVE_V18",
        "v19_stage_size": str(FAP_BYTES),
        "v19_stage_sha256_full_readback_twice": FAP_SHA,
        "active_v18": "FINAL_UNCHANGED_MD5_AND_SIZE_PASS",
        "old_e11_device_backup": "PRESERVED_AND_PINNED",
        "firmware_js_manifest_label": "PINNED_SCREEN_ONLY_NOT_FIRMWARE_ABI_ATTESTATION",
        "future_recovery_filename": "ABSENT",
        "v19_active": "NO",
        "device_writes": "ZERO",
        "automatic_retry_rollback_rename": "ZERO",
        "activation_authorized": "NO",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", required=True)
    p.add_argument("--momentum-scripts", type=Path, required=True)
    p.add_argument("--old-candidate", type=Path, required=True)
    p.add_argument("--saved-old-fap-backup", type=Path, required=True)
    p.add_argument("--final-v18-fap", type=Path, required=True)
    p.add_argument("--active-v18-backup", type=Path, required=True)
    p.add_argument("--data-snapshot", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    args = p.parse_args()
    print("V19 E11 INDEPENDENT REAL POST-STAGE STATE SCREEN - STRICT READ ONLY")
    try:
        if args.port != "COM7":
            raise ValueError("post-stage screen only permits previously verified COM7")
        count, total = verify_backups(
            args.active_v18_backup, args.saved_old_fap_backup,
            args.data_snapshot
        )
        if (count, total) != (12, 2128):
            raise ValueError("PC snapshot drift")
        local_fap = verified_candidate(args.candidate)
        post, js, v18_md5 = check_local(
            args.final_v18_fap, args.saved_old_fap_backup,
            args.old_candidate
        )
        root = args.momentum_scripts
        native = root / "flipper" / "storage.py"
        if root.is_symlink() or native.is_symlink() or not native.is_file():
            raise ValueError("pinned native CLI transport missing/unsafe")
        sys.path.insert(0, str(root.resolve()))
        import flipper.storage as sdk
        verify_transport_origin(sdk.__file__, root)
        client = sdk.FlipperStorage(args.port)
        client.read = DeadlineRead(client.port, timeout_seconds=40)
        with client as connected:
            report = attest_poststage(connected, post, js, v18_md5, local_fap)
    except Exception as exc:
        reason = str(exc) if type(exc) is ValueError else type(exc).__name__
        print("V19 E11 POST-STAGE READ-ONLY NO-GO: " + reason, file=sys.stderr)
        print("STOP. DO NOT RETRY STAGE, RENAME, DELETE, RESTORE OR FLASH.", file=sys.stderr)
        return 1
    for key, value in report.items():
        print(key + ": " + str(value))
    print("V19 E11 INDEPENDENT POST-STAGE READ-ONLY PASS")
    print("V18 STILL ACTIVE, V19 STAGED ONLY; ACTIVATION NOT AUTHORIZED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
