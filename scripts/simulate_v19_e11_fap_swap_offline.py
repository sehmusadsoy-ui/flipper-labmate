#!/usr/bin/env python3
"""LabMate v1.9 E11 FAP-only staging/activation/rollback-state SIMULATOR.

COMPLETELY OFFLINE. No transport import or calls, no USB/COM, no Flipper CLI,
no filesystem writes. Reads THREE immutable PC FAPs and simulates all
transitions strictly IN MEMORY. Not an installer or a rollback executor.

The two same-directory rename steps are separate; failure between them can
temporarily remove LabMate from the installed apps path. Never automatically
retry/delete/restore based on partial or ambiguous evidence.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
import sys

NEW = "/ext/apps/Tools/labmate.v19-new-stage"
ACTIVE = "/ext/apps/Tools/labmate.fap"
CURRENT_BACKUP = "/ext/apps/Tools/labmate.v18-final-before-v19.bak"
LEGACY_BACKUP = "/ext/apps/Tools/labmate.e11-pre-final.bak"
# Reserved ONLY if a separately approved MANUAL rollback is requested.
FAILED_V19_BACKUP = "/ext/apps/Tools/labmate.v19-failed-before-rollback.bak"

V19_SIZE = 97540
V19_SHA = "e1f43390c4078fbaad7e13124331926e0d6667294f2815e8b63762bd16f3ff90"
V18_SIZE = 81528
V18_SHA = "393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61"
LEGACY_SIZE = 81532
LEGACY_SHA = "2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0"
CHUNK = 1024


class TrialStop(ValueError):
    """Stop; preserve *state* in memory to demonstrate nonautomatic recovery."""

    def __init__(self, cause: str, state: "Snapshot") -> None:
        super().__init__(cause)
        self.state = state


@dataclass(frozen=True)
class Snapshot:
    active: bytes | None
    stage: bytes | None
    v18_backup: bytes | None
    legacy_backup: bytes | None
    failed_v19_backup: bytes | None = None


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def matched(data: bytes | None, expected_size: int, expected_sha: str) -> bool:
    return type(data) is bytes and len(data) == expected_size and sha256(data) == expected_sha


def check(data: bytes | None, n: int, sha: str, role: str) -> None:
    if not matched(data, n, sha):
        raise ValueError(role + " differs from pinned byte size / SHA256")


def verified_pc_artifact(path: Path, n: int, sha: str) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size != n:
        raise ValueError("trusted PC FAP missing/unsafe/unexpected size: " + path.name)
    data = path.read_bytes()
    check(data, n, sha, "PC FAP " + path.name)
    return data


def initial_state(v18: bytes, legacy: bytes) -> Snapshot:
    check(v18, V18_SIZE, V18_SHA, "current FINAL v1.8")
    check(legacy, LEGACY_SIZE, LEGACY_SHA, "preserved historical E11 FAP")
    return Snapshot(v18, None, None, legacy)


def state_of(state: Snapshot) -> str:
    if not matched(state.legacy_backup, LEGACY_SIZE, LEGACY_SHA):
        return "UNKNOWN_STOP"

    if matched(state.active, V18_SIZE, V18_SHA) and state.v18_backup is None:
        if state.stage is None:
            if state.failed_v19_backup is None:
                return "ORIGINAL_V18_ACTIVE"
            if matched(state.failed_v19_backup, V19_SIZE, V19_SHA):
                return "ROLLED_BACK_TO_V18_V19_PRESERVED"
        if state.failed_v19_backup is None:
            if matched(state.stage, V19_SIZE, V19_SHA):
                return "V19_STAGED_V18_ACTIVE"
            return "PARTIAL_STAGE_V18_ACTIVE_STOP"
    if (state.active is None and
            matched(state.stage, V19_SIZE, V19_SHA) and
            matched(state.v18_backup, V18_SIZE, V18_SHA) and
            state.failed_v19_backup is None):
        return "BETWEEN_RENAMES_ACTIVE_ABSENT_STOP"
    if (matched(state.active, V19_SIZE, V19_SHA) and state.stage is None and
            matched(state.v18_backup, V18_SIZE, V18_SHA) and
            state.failed_v19_backup is None):
        return "V19_ACTIVE_WITH_V18_BACKUP"
    if (state.active is None and state.stage is None and
            matched(state.v18_backup, V18_SIZE, V18_SHA) and
            matched(state.failed_v19_backup, V19_SIZE, V19_SHA)):
        return "MANUAL_ROLLBACK_BETWEEN_RENAMES_STOP"
    return "UNKNOWN_STOP"


def stage_only(state: Snapshot, candidate: bytes, *, fault: str = "none") -> Snapshot:
    """One virtual append-only stage; current v1.8 not modified."""
    if state_of(state) != "ORIGINAL_V18_ACTIVE":
        raise TrialStop("stage path occupied or original identity changed; no write", state)
    check(candidate, V19_SIZE, V19_SHA, "new v1.9 candidate")
    if fault == "bad-ready":
        raise TrialStop("unexpected Ready response before virtual write; no write", state)
    if fault not in ("none", "short-first-chunk", "bad-ready", "last-byte-corrupt"):
        raise ValueError("unsupported simulated fault")
    result = b""
    for offset in range(0, len(candidate), CHUNK):
        piece = candidate[offset:offset + CHUNK]
        if fault == "short-first-chunk" and offset == 0:
            result += piece[:-1]
            failed = replace(state, stage=result)
            raise TrialStop("short virtual first write; no automatic retry", failed)
        result += piece
    if fault == "last-byte-corrupt":
        result = result[:-1] + bytes((result[-1] ^ 1,))
    staged = replace(state, stage=result)
    if not matched(staged.stage, V19_SIZE, V19_SHA):
        raise TrialStop("virtual staged hash mismatch; no activation", staged)
    if state_of(staged) != "V19_STAGED_V18_ACTIVE":
        raise TrialStop("active v1.8 or historical backup changed during stage", staged)
    return staged


def first_rename(state: Snapshot) -> Snapshot:
    """Virtual ACTIVE v1.8 -> dedicated, EMPTY final-v1.8 backup; no overwrite."""
    if state_of(state) != "V19_STAGED_V18_ACTIVE":
        raise TrialStop("wrong source/backup state; first rename prohibited", state)
    # Preserve historical E11 v1.8DEV .bak; this uses a DIFFERENT new name.
    moved = replace(state, active=None, v18_backup=state.active)
    if state_of(moved) != "BETWEEN_RENAMES_ACTIVE_ABSENT_STOP":
        raise TrialStop("first rename postcondition mismatch; STOP", moved)
    return moved


def second_rename(state: Snapshot) -> Snapshot:
    """Virtual verified STAGE -> ACTIVE; never do this before first rename."""
    if state_of(state) != "BETWEEN_RENAMES_ACTIVE_ABSENT_STOP":
        raise TrialStop("wrong stage/backup state; second rename prohibited", state)
    moved = replace(state, active=state.stage, stage=None)
    if state_of(moved) != "V19_ACTIVE_WITH_V18_BACKUP":
        raise TrialStop("second rename postcondition mismatch; STOP", moved)
    return moved



def manual_recover_first_rename_interruption(state: Snapshot) -> Snapshot:
    """MANUAL VIRTUAL model only; require fresh evidence and express separate consent.

    Between first and second promotion renames, old app path is empty. Restore
    original v1.8 only into this ABSENT path; do not touch v1.9 stage or E11 bak.
    """
    if state_of(state) != "BETWEEN_RENAMES_ACTIVE_ABSENT_STOP":
        raise TrialStop("interrupted first-rename recovery not in exact state", state)
    recovered = replace(state, active=state.v18_backup, v18_backup=None)
    if state_of(recovered) != "V19_STAGED_V18_ACTIVE":
        raise TrialStop("manual virtual interrupted-state recovery failed", recovered)
    return recovered


def manual_rollback_first_rename(state: Snapshot) -> Snapshot:
    """MANUAL virtual v1.9 app -> fresh FAILED_V19_BACKUP. Not a device CLI call."""
    if state_of(state) != "V19_ACTIVE_WITH_V18_BACKUP":
        raise TrialStop("manual rollback first move refused by state", state)
    if state.failed_v19_backup is not None:
        raise TrialStop("would overwrite reserved failed-v1.9 backup", state)
    moved = replace(state, active=None, failed_v19_backup=state.active)
    if state_of(moved) != "MANUAL_ROLLBACK_BETWEEN_RENAMES_STOP":
        raise TrialStop("manual rollback first move postcondition failed", moved)
    return moved


def manual_rollback_second_rename(state: Snapshot) -> Snapshot:
    """MANUAL virtual preserved v1.8 backup -> empty active; no cleanup."""
    if state_of(state) != "MANUAL_ROLLBACK_BETWEEN_RENAMES_STOP":
        raise TrialStop("manual rollback second move refused by state", state)
    recovered = replace(state, active=state.v18_backup, v18_backup=None)
    if state_of(recovered) != "ROLLED_BACK_TO_V18_V19_PRESERVED":
        raise TrialStop("manual virtual rollback failed to preserve app pair", recovered)
    return recovered


def run_virtual_scenarios(v18: bytes, legacy: bytes, candidate: bytes) -> dict[str, str]:
    start = initial_state(v18, legacy)
    check(candidate, V19_SIZE, V19_SHA, "reviewed v1.9 FAP")
    passed: dict[str, str] = {}
    stage = stage_only(start, candidate)
    if state_of(stage) != "V19_STAGED_V18_ACTIVE":
        raise ValueError("clean virtual stage not verified")
    passed["CLEAN_STAGE"] = "PASS"
    in_between = first_rename(stage)
    if state_of(in_between) != "BETWEEN_RENAMES_ACTIVE_ABSENT_STOP":
        raise ValueError("between-renames interruption not classified")
    passed["INTERRUPTION_AFTER_FIRST_RENAME"] = "STOP_PRESERVES_STAGED_V19_AND_V18_BACKUP"
    final = second_rename(in_between)
    if (state_of(final) != "V19_ACTIVE_WITH_V18_BACKUP" or
            final.v18_backup != v18 or final.legacy_backup != legacy):
        raise ValueError("virtual promotion lost original recovery artifacts")

    passed["CLEAN_VIRTUAL_PROMOTION"] = "PASS_WITH_V18_AND_LEGACY_BACKUPS"
    # Deliberately requested MANUAL recovery sequences. These are virtual
    # rehearsals only; never invoke device-side recovery automatically.
    recovered_gap = manual_recover_first_rename_interruption(in_between)
    if (recovered_gap.active != v18 or recovered_gap.stage != candidate or
            recovered_gap.legacy_backup != legacy):
        raise ValueError("virtual manual between-renames recovery lost artifacts")
    passed["MANUAL_GAP_RECOVERY_MODEL"] = "PASS_ONLY_WITH_SEPARATE_CONSENT"
    rb_gap = manual_rollback_first_rename(final)
    if state_of(rb_gap) != "MANUAL_ROLLBACK_BETWEEN_RENAMES_STOP":
        raise ValueError("manual rollback first move not correctly classified")
    rolled_back = manual_rollback_second_rename(rb_gap)
    if (rolled_back.active != v18 or rolled_back.failed_v19_backup != candidate or
            rolled_back.legacy_backup != legacy):
        raise ValueError("virtual manual rollback did not preserve both FAPs")
    passed["MANUAL_VIRTUAL_ROLLBACK_MODEL"] = "PASS_ONLY_WITH_SEPARATE_CONSENT"
    for fault, label, expected in (
        ("bad-ready", "BAD_READY", "ORIGINAL_V18_ACTIVE"),
        ("short-first-chunk", "SHORT_WRITE", "PARTIAL_STAGE_V18_ACTIVE_STOP"),
        ("last-byte-corrupt", "STAGED_SHA_MISMATCH", "PARTIAL_STAGE_V18_ACTIVE_STOP"),
    ):
        try:
            stage_only(start, candidate, fault=fault)
        except TrialStop as exc:
            if state_of(exc.state) != expected or exc.state.active != v18:
                raise ValueError("fault did not preserve active v1.8: " + fault)
            passed[label] = "FAIL_CLOSED_OLD_V18_ACTIVE"
        else:
            raise ValueError("virtual fault incorrectly passed: " + fault)
    # A second attempt on a partial stage must FAIL; never append again.
    try:
        stage_only(replace(start, stage=b"partial"), candidate)
    except TrialStop:
        passed["NO_BLIND_STAGE_RETRY"] = "PASS"
    else:
        raise ValueError("blind stage retry was not rejected")
    return passed


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--current-v18-pc-backup", type=Path, required=True)
    p.add_argument("--legacy-e11-pc-backup", type=Path, required=True)
    args = p.parse_args()
    print("LABMATE v1.9 E11 FAP-SWAP VIRTUAL SIMULATOR - OFFLINE ONLY")
    try:
        new = verified_pc_artifact(args.candidate, V19_SIZE, V19_SHA)
        old = verified_pc_artifact(args.current_v18_pc_backup, V18_SIZE, V18_SHA)
        prior = verified_pc_artifact(args.legacy_e11_pc_backup, LEGACY_SIZE, LEGACY_SHA)
        report = run_virtual_scenarios(old, prior, new)
    except Exception as exc:
        reason = str(exc) if type(exc) is ValueError else type(exc).__name__
        print("V19 OFFLINE SWAP SIMULATION NO-GO: " + reason, file=sys.stderr)
        print("NO DEVICE/PC CHANGES. DO NOT INSTALL.", file=sys.stderr)
        return 1
    for key, value in report.items():
        print(key + ": " + value)
    print("V19 VIRTUAL STAGE/TWO-RENAME AND MANUAL ROLLBACK MODELS: PASS")
    print("USB_CALLS: ZERO; DEVICE_WRITES: ZERO; PC_WRITES: ZERO")
    print("REAL COM WRITE TOOL / REAL DEVICE TRIAL: NOT AUTHORIZED OR EXECUTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
