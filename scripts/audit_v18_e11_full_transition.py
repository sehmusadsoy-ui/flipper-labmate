#!/usr/bin/env python3
"""Predict ONLY the E11 full updater's LabMate FAP resource transition.

Sources: owner-reported real OLD Flipper /ext/Manifest summary + actual
SHA256-pinned full E11 updater archive and its packed NEW Manifest.
This models old FILE resource cleanup followed by new resource extraction.
It does NOT authorize a trial or claim successful device boot/recovery.
No Flipper serial, SD, updater or filesystem writes.
"""
from __future__ import annotations
import argparse
from pathlib import Path

from check_v18_e11_split_trial_gate import EVIDENCE, analyze_report
from audit_v18_e11_packed_manifest_integrity import (
    check_consistency, _archive_member_sha, scan_packed_resources
)
from audit_v18_e11_resource_impact import FAP_PATH
from preflight_v18_e11_local import ARTIFACTS, assert_sha
from stage_v18_e11_review_only import inspect_updater

def model_old_to_new_transition(old_report: dict[str, str], resources: bytes) -> dict[str, str]:
    if old_report.get("old_manifest_explicitly_lists_labmate_fap") != "YES":
        raise ValueError("real old resource Manifest must establish previous app cleanup")
    if old_report.get("firmware_trial_authorized") != "NO":
        raise ValueError("operator old Manifest audit must never grant flash authorization")
    if old_report.get("evidence_origin") != "OPERATOR_REPORTED_REAL_COM7_READ_ONLY_MD5_SCREEN":
        raise ValueError("expected real-device read-only evidence provenance missing")
    result = check_consistency(
        resources,
        should_include_fap=True,
        expected_fap_sha256=ARTIFACTS["labmate.fap"],
        expected_js_sha256=ARTIFACTS["js_gpio.module"],
    )
    members, records = scan_packed_resources(resources)
    fap = FAP_PATH.casefold()
    if fap not in members or fap not in records:
        raise ValueError("matched E11 application missing from new resources")
    if result["packed_manifest_orphan_references"] != 0 or result["packed_manifest_wrong_file_md5_or_size"] != 0:
        raise ValueError("full E11 resource Manifest inconsistent")
    if _archive_member_sha(resources, FAP_PATH) != ARTIFACTS["labmate.fap"]:
        raise ValueError("new LabMate FAP differs from pinned build")
    return {
        "old_installed_fap_listed_for_cleanup": "YES",
        "new_packed_fap_present_and_declared": "YES",
        "new_packed_fap_sha256_matches_reviewed_build": "YES",
        "resource_phase_expected_result": "OLD_EXITFIX_TARGETED_NEW_E11_FAP_SUPPLIED",
        "full_updater_guarantees_boot": "NO",
        "exact_previous_custom_firmware_rollback_proven": "NO",
        "on_device_e11_lease_tests_completed": "NO",
        "user_install_authorized": "NO",
        "physical_trial_result": "NOT_PERFORMED",
    }

def verify_exact_candidate(candidate: Path, evidence: Path = EVIDENCE) -> dict[str, str]:
    # Verify independent exact artifact identity, never accept arbitrary TAR.
    if not candidate.is_dir() or candidate.is_symlink():
        raise ValueError("exact official E11 review artifact directory required")
    assert_sha(candidate / "firmware-full-update.tgz", ARTIFACTS["firmware-full-update.tgz"])
    assert_sha(candidate / "firmware.dfu", ARTIFACTS["firmware.dfu"])
    assert_sha(candidate / "labmate.fap", ARTIFACTS["labmate.fap"])
    assert_sha(candidate / "js_gpio.module", ARTIFACTS["js_gpio.module"])
    full = inspect_updater(candidate / "firmware-full-update.tgz")
    previous = analyze_report(evidence.read_text(encoding="utf-8"))
    return model_old_to_new_transition(previous, full["resources.tar.gz"])

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", type=Path, required=True)
    args = p.parse_args()
    try:
        result = verify_exact_candidate(args.candidate)
    except (OSError, ValueError, UnicodeError) as exc:
        p.exit(1, "E11 OFFLINE FULL TRANSITION REFUSED - NO FLASH: " + type(exc).__name__ + "\n")
    for k, v in result.items():
        print(k + ": " + v)
    print("E11 OFFLINE FULL FIRMWARE/FAP RESOURCE TRANSITION MODEL PASS - DEVICE TRIAL NOT AUTHORIZED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
