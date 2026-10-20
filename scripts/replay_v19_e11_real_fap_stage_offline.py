#!/usr/bin/env python3
"""Replay ACTUAL stage_v19_e11_sidecar_only.stage_only on an in-memory fake.

Reads exact three previously archived PC FAP binaries; NEVER opens USB/COM,
imports any Flipper serial transport, flashes or changes PC/device files.
Patches ONLY remote identity-audit functions (FakeCLI has no E11 device_info
response); runs the real stage-only orchestration, binary chunk sender,
double device-readback verification and post-stage active/backup checks.

Important limitations: FakeCLI is NOT the installed native Momentum CLI.
This is neither device-write authorization nor independent firmware ABI proof.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from unittest.mock import patch

import simulate_v19_e11_storage_cli_offline as fixture
import stage_v19_e11_sidecar_only as stage
from simulate_v19_e11_fap_swap_offline import (
    V19_SIZE, V19_SHA, V18_SIZE, V18_SHA,
    LEGACY_SIZE, LEGACY_SHA, verified_pc_artifact,
)

# For reproducibility this file loads source binaries ONLY from PC and does
# not call stage.main() / FlipperStorage / open or write any device file.
CORRECT_RESOURCE_AUDIT = {
    "state": "AFTER_PROMOTION",
    "new_v18_FAP": "ACTIVE_MD5_AND_SIZE_PASS",
    "old_E11_FAP_preserved": "PC_BACKUP_AND_DEVICE_BAK",
    "firmware_JS_gpio_eventloop_manifest": "PINNED_MD5_AND_LABEL_MATCH",
}
ACCEPTED_FAULTS = frozenset((
    "bad-ready", "echo-fail", "short-first-chunk",
    "chunk-tail-fail", "stage-md5-bad", "stage-readback-corrupt",
))


def replay(candidate: bytes, current_v18: bytes, legacy: bytes,
           *, faults: frozenset[str] = frozenset()) -> tuple[fixture.FakeCLI, dict]:
    """Invoke the candidate *stage-only* code on FakeCLI, not a device."""
    if not faults <= ACCEPTED_FAULTS:
        raise ValueError("unapproved virtual fault flag")
    # Crucially reuse the immutable size/hash constants in the source model,
    # not a checksum synthesized from the incoming data.
    for data, size, digest, desc in (
        (candidate, V19_SIZE, V19_SHA, "v1.9 candidate"),
        (current_v18, V18_SIZE, V18_SHA, "active v1.8 backup"),
        (legacy, LEGACY_SIZE, LEGACY_SHA, "historical E11 v1.8DEV backup"),
    ):
        if type(data) is not bytes or len(data) != size or fixture.sha(data) != digest:
            raise ValueError("unverified PC input to stage-only replay: " + desc)
    fake = fixture.FakeCLI(current_v18, legacy, set(faults))
    preflight = {"v19_reserved_paths": "BOTH_ABSENT_TWICE"}
    post = {"E11_APP": fixture.md5(legacy)}
    js = {}
    actual_v18_md5 = fixture.md5(current_v18)

    # These are only the native-resource audit functions FakeCLI cannot
    # simulate. The stage code itself drives REAL app/backup stat/MD5,
    # all 24 exact chunk commands, Ready/echo/tail checks, 2 full readbacks.
    with patch.object(stage, "attest_current_v18_and_free_names",
                      return_value=preflight) as before, patch.object(
                          stage, "audit", return_value=CORRECT_RESOURCE_AUDIT
                      ) as after:
        result = stage.stage_only(fake, candidate, post, js, actual_v18_md5)
    if before.call_count != 1 or after.call_count != 1:
        raise ValueError("pre/post native audit mock boundary unexpectedly changed")
    if fake.rename_count != 0 or fake.fs != {
        stage.APP: current_v18,
        stage.LEGACY: legacy,
        stage.STAGE: candidate,
    }:
        raise ValueError("stage-only replay changed active app or on-device backup")
    if fake.chunk_count != (len(candidate) + stage.BUF - 1) // stage.BUF:
        raise ValueError("stage-only replay had incomplete/unexpected chunk count")
    if any(not command.startswith(("storage stat ", "storage write_chunk "))
           for command in fake.commands):
        raise ValueError("unexpected native CLI command in stage-only replay")
    if any(command.startswith("storage write_chunk ") and
           f'"{stage.STAGE}"' not in command for command in fake.commands):
        raise ValueError("stage replay wrote a forbidden pathname")
    if (result.get("stage_only") != "PASS_FULL_DEVICE_BINARY_READBACK" or
            result.get("v19_active") != "NO" or
            result.get("rename_performed") != "NO" or
            result.get("active_app") != "FINAL_V18_UNCHANGED"):
        raise ValueError("stage-only review unexpectedly changed declared behavior")
    return fake, result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", required=True, type=Path)
    p.add_argument("--current-v18-pc-backup", required=True, type=Path)
    p.add_argument("--legacy-e11-pc-backup", required=True, type=Path)
    args = p.parse_args()
    print("V19 E11 REAL-FAP STAGE-ONLY REPLAY - IN MEMORY / NEVER DEVICE")
    try:
        candidate = verified_pc_artifact(args.candidate, V19_SIZE, V19_SHA)
        old = verified_pc_artifact(args.current_v18_pc_backup, V18_SIZE, V18_SHA)
        legacy = verified_pc_artifact(args.legacy_e11_pc_backup, LEGACY_SIZE, LEGACY_SHA)
        virtual, result = replay(candidate, old, legacy)
    except Exception as exc:
        reason = str(exc) if type(exc) is ValueError else type(exc).__name__
        print("V19 REAL-FAP STAGE-ONLY REPLAY NO-GO: " + reason, file=sys.stderr)
        print("STOP: no device operation or installation approved.", file=sys.stderr)
        return 1
    print("FAP_CANDIDATE_BYTES:", len(candidate))
    print("FAP_CANDIDATE_SHA256:", V19_SHA)
    print("STAGE_CHUNKS:", virtual.chunk_count)
    print("STAGE_ONLY_FULL_READBACK_TWICE:", "PASS")
    print("ACTIVE_FINAL_V18_UNCHANGED:", "YES")
    print("LEGACY_E11_BACKUP_UNCHANGED:", "YES")
    print("RENAME_ATTEMPTS:", virtual.rename_count)
    print("REAL_FAP_ACTUAL_STAGE_CODE_OFFLINE_REPLAY: PASS")
    print("USB_CALLS: 0 | DEVICE_WRITES: 0 | PC_WRITES: 0")
    print("NATIVE_E11_FIRMWARE_ABI: NOT_ATTESTED | INSTALL: NOT_AUTHORIZED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
