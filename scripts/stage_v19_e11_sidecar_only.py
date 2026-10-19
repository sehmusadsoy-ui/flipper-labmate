#!/usr/bin/env python3
"""v1.9 E11 OPTIONAL STAGE ONLY — device write, NOT authorized by this script.

WARNING: This is a REVIEW-ONLY proposed device-writing program. It must NOT
be executed until mock tests, pinned local source/transport audit, live
compatibility and final explicit operator permission are all separately
accepted. Its only allowed device write is:
  storage write_chunk "/ext/apps/Tools/labmate.v19-new-stage" N
as a NEW non-.fap sidecar only when absent. The currently ACTIVE v1.8 final
FAP and both v1.8 backups stay unchanged; NO promotion, rename, removal,
firmware flash or automatic cleanup/rollback/retry.

A short/ambiguous write leaves the partial sidecar ON DEVICE, and the user
must STOP and inspect read-only state before any further action.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from backup_v19_active_v18_fap_ro import check_local
from check_v18_e11_phase2b_state_readonly import audit
from check_v19_e11_device_prewrite_ro import (
    PROPOSED_STAGE, PROPOSED_FINAL_V18_BACKUP,
    attest_current_v18_and_free_names, stat_reserved_absent,
)
from prepare_v19_e11_pc_only import (
    FAP_BYTES, FAP_SHA, verify_backups,
)

BUF = 4096
V18_ACTIVE_BYTES = 81528
APP = "/ext/apps/Tools/labmate.fap"
LEGACY = "/ext/apps/Tools/labmate.e11-pre-final.bak"
STAGE = PROPOSED_STAGE
BACKUP = PROPOSED_FINAL_V18_BACKUP
MD5_HEX = re.compile(r"[0-9a-f]{32}\Z")
AUTHORIZATION = "I_APPROVE_V19_STAGE_ONLY_NONAPP_SIDECAR"
if len({APP, LEGACY, STAGE, BACKUP}) != 4:
    raise ValueError("dangerous overlapping device paths")


def verified_candidate(path: Path) -> bytes:
    """Must be exactly the locally built and PC rehashed WSL-reviewed FAP."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size != FAP_BYTES:
        raise ValueError("missing/unsafe/replaced v1.9 staged PC FAP")
    data = path.read_bytes()
    if len(data) != FAP_BYTES or hashlib.sha256(data).hexdigest() != FAP_SHA:
        raise ValueError("v1.9 staged PC FAP content changed")
    return data


def stat_exact(client, path: str) -> bytes:
    if path not in (STAGE, APP, BACKUP):
        raise ValueError("unexpected device stat pathname")
    if client.CLI_EOL != "\r\n" or client.CLI_PROMPT != ">: ":
        raise ValueError("unexpected native serial CLI framing")
    cmd = f'storage stat "{path}"'
    echoed = client.send_and_wait_eol(cmd + "\r")
    if echoed != cmd.encode("ascii"):
        raise ValueError("unexpected native stat echo")
    response = client.read.until(client.CLI_EOL)
    tail = client.read.until(client.CLI_PROMPT)
    if tail != b"\r\n":
        raise ValueError("unexpected native stat tail")
    return response


def require_md5(client, path: str, expected: str) -> None:
    if path not in (STAGE, APP):
        raise ValueError("unexpected remote MD5 pathname")
    digest = client.hash_flipper(path).lower().strip()
    if MD5_HEX.fullmatch(digest) is None or digest != expected:
        raise ValueError("remote SD MD5 mismatch: " + path)


def send_stage_chunk(client, part: bytes) -> None:
    """APPEND *only* to predetermined new v1.9 non-app sidecar."""
    if type(part) is not bytes or not 1 <= len(part) <= BUF:
        raise ValueError("invalid binary stage chunk")
    if client.CLI_EOL != "\r\n" or client.CLI_PROMPT != ">: ":
        raise ValueError("unexpected native serial CLI framing")
    cmd = f'storage write_chunk "{STAGE}" {len(part)}'
    echo = client.send_and_wait_eol(cmd + "\r")
    if echo != cmd.encode("ascii"):
        raise ValueError("unexpected device CLI echo — STOP BEFORE BINARY")
    ready = client.read.until(client.CLI_EOL)
    if ready != b"Ready":
        raise ValueError("native CLI Ready mismatch — STOP BEFORE BINARY")
    count = client.port.write(part)
    if count != len(part):
        raise ValueError("short serial write — STOP; no automatic retry")
    client.port.flush()
    final = client.read.until(client.CLI_PROMPT)
    if final != b"\r\n":
        raise ValueError("ambiguous native CLI write result — STOP")


def verify_staged(client, candidate: bytes) -> None:
    """Re-read FULL staged FAP from device, never rely only on MD5/stat."""
    expected = f"File, size: {FAP_BYTES}b".encode("ascii")
    if stat_exact(client, STAGE) != expected:
        raise ValueError("staged device size mismatch, no promotion")
    md5 = hashlib.md5(candidate).hexdigest()
    require_md5(client, STAGE, md5)
    read = client.read_file(STAGE)
    if not isinstance(read, (bytes, bytearray)):
        raise ValueError("remote stage readback did not return binary")
    result = bytes(read)
    if len(result) != FAP_BYTES or hashlib.sha256(result).hexdigest() != FAP_SHA:
        raise ValueError("staged device full SHA256 readback mismatch")
    if result != candidate:
        raise ValueError("staged device bytes differ despite checksum")
    require_md5(client, STAGE, md5)


def stage_only(client, candidate: bytes, post: dict, js: dict, v18_md5: str) -> dict:
    """After preflight, the only writer is send_stage_chunk(STAGE)."""
    if type(candidate) is not bytes or len(candidate) != FAP_BYTES or hashlib.sha256(candidate).hexdigest() != FAP_SHA:
        raise ValueError("wrong v1.9 FAP source")
    # Independently verify the installed E11 resources and original v1.8
    # app+backups BEFORE touching the new sidecar name.
    first = attest_current_v18_and_free_names(client, post, js, v18_md5)
    if first["v19_reserved_paths"] != "BOTH_ABSENT_TWICE":
        raise ValueError("both new device sidecar names must be absent twice")
    stat_reserved_absent(client, STAGE)
    stat_reserved_absent(client, BACKUP)

    for offset in range(0, FAP_BYTES, BUF):
        send_stage_chunk(client, candidate[offset:offset + BUF])

    verify_staged(client, candidate)
    # Old phase2b audit is still valid: it watches the DIFFERENT original
    # v1.8 E11 sidecar paths, which must be unchanged by this new stage.
    final = audit(client, post, js, post["E11_APP"], v18_md5)
    if final["state"] != "AFTER_PROMOTION" or final["new_v18_FAP"] != "ACTIVE_MD5_AND_SIZE_PASS":
        raise ValueError("active final v1.8 is no longer unchanged — STOP")
    if final["firmware_JS_gpio_eventloop_manifest"] != "PINNED_MD5_AND_LABEL_MATCH":
        raise ValueError("native E11 resources changed — STOP")
    if final["old_E11_FAP_preserved"] != "PC_BACKUP_AND_DEVICE_BAK":
        raise ValueError("historic E11 device backup changed — STOP")
    if stat_exact(client, APP) != f"File, size: {V18_ACTIVE_BYTES}b".encode("ascii"):
        raise ValueError("original v1.8 active size drift")
    require_md5(client, APP, v18_md5)
    stat_reserved_absent(client, BACKUP)
    verify_staged(client, candidate)
    stat_reserved_absent(client, BACKUP)
    return {
        "stage_only": "PASS_FULL_DEVICE_BINARY_READBACK",
        "stage_path": STAGE,
        "stage_fap_sha256": FAP_SHA,
        "stage_fap_bytes": FAP_BYTES,
        "active_app": "FINAL_V18_UNCHANGED",
        "old_e11_device_backup": "UNCHANGED",
        "v19_active": "NO",
        "rename_performed": "NO",
        "firmware_flash": "NO",
        "user_data_modified": "NO",
        "next_action": "STOP_FOR_SEPARATE_V19_ACTIVATION_APPROVAL",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", required=True)
    p.add_argument("--momentum-scripts", required=True, type=Path)
    p.add_argument("--old-candidate", required=True, type=Path)
    p.add_argument("--saved-old-fap-backup", required=True, type=Path)
    p.add_argument("--final-v18-fap", required=True, type=Path)
    p.add_argument("--active-v18-backup", required=True, type=Path)
    p.add_argument("--data-snapshot", required=True, type=Path)
    p.add_argument("--candidate", required=True, type=Path)
    p.add_argument("--authorize-stage-only", required=True)
    args = p.parse_args()
    print("V19 E11 POTENTIAL DEVICE WRITE: STAGE ONE NEW NON-.FAP SIDECAR ONLY")
    print("NO APP ACTIVATION; NO RENAME; NO FIRMWARE OR LABMATE DATA WRITE")
    print("WARNING: a failed USB write may leave a partial stage. NEVER blindly retry.")
    try:
        if args.authorize_stage_only != AUTHORIZATION:
            raise ValueError("EXPLICIT and EXACT separate stage-only authorization missing")
        if not re.fullmatch(r"COM[1-9][0-9]{0,2}", args.port):
            raise ValueError("exact expected COMn port required")
        candidate = verified_candidate(args.candidate)
        verify_backups(args.active_v18_backup, args.saved_old_fap_backup, args.data_snapshot)
        post, js, v18_md5 = check_local(
            args.final_v18_fap, args.saved_old_fap_backup, args.old_candidate
        )
        root = args.momentum_scripts
        library = root / "flipper" / "storage.py"
        if root.is_symlink() or library.is_symlink() or not library.is_file():
            raise ValueError("pinned native CLI transport missing")
        sys.path.insert(0, str(root.resolve()))
        import flipper.storage as sdk
        verify_transport_origin(sdk.__file__, root)
        client = sdk.FlipperStorage(args.port)
        client.read = DeadlineRead(client.port, timeout_seconds=40)
        client.port.write_timeout = 12
        with client as connected:
            report = stage_only(connected, candidate, post, js, v18_md5)
    except Exception as exc:
        reason = str(exc) if type(exc) is ValueError else type(exc).__name__
        print("V19 E11 DEVICE STAGE-ONLY NO-GO: " + reason, file=sys.stderr)
        print("STOP. DO NOT RETRY, DELETE, RENAME, RESTORE OR FLASH.", file=sys.stderr)
        print("The original final v1.8 app may remain active; check only by new read-only reconciliation.", file=sys.stderr)
        return 1
    for key, value in report.items():
        print(key + ": " + str(value))
    print("V19 E11 STAGED SIDEcar VERIFIED; v1.8 STILL ACTIVE; STOP FOR REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
