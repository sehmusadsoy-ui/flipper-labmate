#!/usr/bin/env python3
"""OFFLINE-only review of the EXACT v1.9 two-rename and v1.8 manual recovery code.

Strictly in-memory native-CLI FakeCLI. Imports NO serial module, opens NO COM,
changes NO device or local files. Treat outputs as a review, NEVER as a grant
to install, rerun, rollback or claim matched internal firmware ABI.
The first and second renames are NOT atomic; any ambiguity STOPS.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys
from unittest.mock import patch

import simulate_v19_e11_storage_cli_offline as fixture
from simulate_v19_e11_fap_swap_offline import (
    ACTIVE, NEW, CURRENT_BACKUP, LEGACY_BACKUP, FAILED_V19_BACKUP,
    V19_SHA, V19_SIZE, V18_SHA, V18_SIZE, LEGACY_SHA, LEGACY_SIZE,
    verified_pc_artifact,
)

ABSENT = fixture.ABSENT
EXPECTED = {
    ACTIVE: (V18_SIZE, V18_SHA),  # original active only; can change after promotion
    NEW: (V19_SIZE, V19_SHA),
    CURRENT_BACKUP: (V18_SIZE, V18_SHA),
    LEGACY_BACKUP: (LEGACY_SIZE, LEGACY_SHA),
    FAILED_V19_BACKUP: (V19_SIZE, V19_SHA),
}
STATUS_PATHS = frozenset(EXPECTED)
FORWARD = frozenset(((ACTIVE, CURRENT_BACKUP), (NEW, ACTIVE)))
BACKWARD = frozenset(((ACTIVE, FAILED_V19_BACKUP), (CURRENT_BACKUP, ACTIVE)))
GAP_RECOVERY = frozenset(((CURRENT_BACKUP, ACTIVE),))
HEX = re.compile(r"[0-9a-f]{32}\Z")


def sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def stat(client, path: str) -> bytes:
    if path not in STATUS_PATHS:
        raise ValueError("forbidden status path")
    if client.CLI_EOL != "\r\n" or client.CLI_PROMPT != ">: ":
        raise ValueError("bad pinned CLI framing")
    command = f'storage stat "{path}"'
    echo = client.send_and_wait_eol(command + "\r")
    if echo != command.encode("ascii"):
        raise ValueError("unknown native stat echo")
    result = client.read.until(client.CLI_EOL)
    tail = client.read.until(client.CLI_PROMPT)
    if tail != b"\r\n":
        raise ValueError("unexpected stat response tail")
    if result not in (
        ABSENT,
        b"File, size: " + str(V18_SIZE).encode("ascii") + b"b",
        b"File, size: " + str(V19_SIZE).encode("ascii") + b"b",
        b"File, size: " + str(LEGACY_SIZE).encode("ascii") + b"b",
    ):
        raise ValueError("ambiguous stat size/error response")
    return result


def exact(client, path: str, data: bytes) -> None:
    if path not in STATUS_PATHS or type(data) is not bytes:
        raise ValueError("invalid fixed exact-file verification")
    size, digest = EXPECTED[path]
    # ACTIVE may be one of the two known FAPs, based only on provided bytes
    if path == ACTIVE:
        if (len(data), sha256(data)) not in ((V18_SIZE, V18_SHA), (V19_SIZE, V19_SHA)):
            raise ValueError("unexpected active FAP identity")
        size, digest = len(data), sha256(data)
    if len(data) != size or sha256(data) != digest:
        raise ValueError("local FAP input differs from fixed identity: " + path)
    if stat(client, path) != f"File, size: {size}b".encode("ascii"):
        raise ValueError("wrong remote FAP byte size at " + path)
    remote_md5 = client.hash_flipper(path).strip().lower()
    if HEX.fullmatch(remote_md5) is None or remote_md5 != hashlib.md5(data).hexdigest():
        raise ValueError("remote checksum mismatch at " + path)
    actual = client.read_file(path)
    if not isinstance(actual, (bytes, bytearray)) or bytes(actual) != data:
        raise ValueError("full binary readback mismatch at " + path)
    if client.hash_flipper(path).strip().lower() != remote_md5:
        raise ValueError("remote file moved while readback: " + path)


def require_absent(client, path: str) -> None:
    if stat(client, path) != ABSENT:
        raise ValueError("required target not absent: " + path)


def state_staged(client, v19: bytes, v18: bytes, legacy: bytes) -> None:
    exact(client, ACTIVE, v18)
    exact(client, NEW, v19)
    exact(client, LEGACY_BACKUP, legacy)
    require_absent(client, CURRENT_BACKUP)
    require_absent(client, FAILED_V19_BACKUP)


def state_between(client, v19: bytes, v18: bytes, legacy: bytes) -> None:
    require_absent(client, ACTIVE)
    exact(client, CURRENT_BACKUP, v18)
    exact(client, NEW, v19)
    exact(client, LEGACY_BACKUP, legacy)
    require_absent(client, FAILED_V19_BACKUP)


def state_activated(client, v19: bytes, v18: bytes, legacy: bytes) -> None:
    exact(client, ACTIVE, v19)
    exact(client, CURRENT_BACKUP, v18)
    exact(client, LEGACY_BACKUP, legacy)
    require_absent(client, NEW)
    require_absent(client, FAILED_V19_BACKUP)


def state_rollback_gap(client, v19: bytes, v18: bytes, legacy: bytes) -> None:
    require_absent(client, ACTIVE)
    exact(client, CURRENT_BACKUP, v18)
    exact(client, FAILED_V19_BACKUP, v19)
    exact(client, LEGACY_BACKUP, legacy)
    require_absent(client, NEW)


def state_rolled_back(client, v19: bytes, v18: bytes, legacy: bytes) -> None:
    exact(client, ACTIVE, v18)
    exact(client, FAILED_V19_BACKUP, v19)
    exact(client, LEGACY_BACKUP, legacy)
    require_absent(client, NEW)
    require_absent(client, CURRENT_BACKUP)


def rename_once(client, source: str, target: str, allowed: frozenset) -> None:
    if (source, target) not in allowed or source == target:
        raise ValueError("rename not strictly allowlisted")
    if stat(client, source) == ABSENT:
        raise ValueError("source vanished before rename")
    require_absent(client, target)
    command = f'storage rename "{source}" "{target}"'
    echo = client.send_and_wait_eol(command + "\r")
    if echo != command.encode("ascii"):
        raise ValueError("ambiguous rename echo: STOP, never repeat")
    reply = client.read.until(client.CLI_PROMPT)
    if reply != b"\r\n":
        raise ValueError("ambiguous rename outcome: STOP, never repeat")


def promote_two_renames(client, v19: bytes, v18: bytes, legacy: bytes) -> dict:
    """Reviewable client-injected algorithm; this file NEVER creates real client."""
    state_staged(client, v19, v18, legacy)
    state_staged(client, v19, v18, legacy)
    rename_once(client, ACTIVE, CURRENT_BACKUP, FORWARD)
    state_between(client, v19, v18, legacy)
    rename_once(client, NEW, ACTIVE, FORWARD)
    state_activated(client, v19, v18, legacy)
    return {"offline_activation": "PASS_TWO_RENAMES", "v18_backup": "PINNED_AND_PRESERVED",
            "old_e11": "PINNED_AND_PRESERVED", "device_writes": "ZERO"}


def recover_interrupted_first_rename(client, v19: bytes, v18: bytes, legacy: bytes) -> None:
    """MANUALLY requested in-memory interruption review, no automatic recovery."""
    state_between(client, v19, v18, legacy)
    rename_once(client, CURRENT_BACKUP, ACTIVE, GAP_RECOVERY)
    state_staged(client, v19, v18, legacy)


def rollback_two_renames(client, v19: bytes, v18: bytes, legacy: bytes) -> None:
    """MANUALLY requested in-memory rollback review, no automatic recovery."""
    state_activated(client, v19, v18, legacy)
    rename_once(client, ACTIVE, FAILED_V19_BACKUP, BACKWARD)
    state_rollback_gap(client, v19, v18, legacy)
    rename_once(client, CURRENT_BACKUP, ACTIVE, BACKWARD)
    state_rolled_back(client, v19, v18, legacy)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", required=True, type=Path)
    p.add_argument("--current-v18-pc-backup", required=True, type=Path)
    p.add_argument("--legacy-e11-pc-backup", required=True, type=Path)
    a = p.parse_args()
    print("V19 E11 ACTUAL RENAME ORCHESTRATION - THREE REAL FAPS, IN MEMORY ONLY")
    try:
        candidate = verified_pc_artifact(a.candidate, V19_SIZE, V19_SHA)
        v18 = verified_pc_artifact(a.current_v18_pc_backup, V18_SIZE, V18_SHA)
        old = verified_pc_artifact(a.legacy_e11_pc_backup, LEGACY_SIZE, LEGACY_SHA)

        # This mock extension exists ONLY here and is NEVER transmitted to device:
        # Production ROM transport has no hidden rollback permission.
        all_mock_renames = frozenset(FORWARD | BACKWARD)
        with patch.object(fixture, "RENAMES", all_mock_renames):
            client = fixture.FakeCLI(v18, old)
            client.fs[NEW] = candidate  # simulate ALREADY-STAGED real state
            result = promote_two_renames(client, candidate, v18, old)
            if client.rename_count != 2:
                raise ValueError("expected exactly 2 simulated promotion renames")
            print("OFFLINE_V19_PROMOTION: " + result["offline_activation"])

            rollback_two_renames(client, candidate, v18, old)
            if client.rename_count != 4:
                raise ValueError("expected 2 promotion and 2 manual rollback renames")
            print("OFFLINE_MANUAL_V18_ROLLBACK: PASS_V19_PRESERVED")

            interrupted = fixture.FakeCLI(v18, old)
            interrupted.fs[NEW] = candidate
            state_staged(interrupted, candidate, v18, old)
            rename_once(interrupted, ACTIVE, CURRENT_BACKUP, FORWARD)
            state_between(interrupted, candidate, v18, old)
            recover_interrupted_first_rename(interrupted, candidate, v18, old)
            if interrupted.rename_count != 2:
                raise ValueError("manual first rename interruption not reviewed")
            print("OFFLINE_MANUAL_INTERRUPTION_RECOVERY: PASS_V18_ACTIVE_AND_V19_STAGED")
    except Exception as exc:
        why = str(exc) if type(exc) is ValueError else type(exc).__name__
        print("V19 E11 OFFLINE ACTIVATION/RECOVERY REVIEW NO-GO: " + why, file=sys.stderr)
        print("STOP; DO NOT INSTALL, FLASH, REPEAT OR AUTO-RESTORE.", file=sys.stderr)
        return 1
    print("USB_CALLS: ZERO | DEVICE_WRITES: ZERO | PC_WRITES: ZERO")
    print("REAL V1.9 ACTIVATION: NOT AUTHORIZED | FIRMWARE ABI: NOT_ATTESTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
