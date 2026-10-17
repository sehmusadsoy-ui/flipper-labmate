#!/usr/bin/env python3
"""Fail-closed E11 trial decision from operator-reported real old Manifest.

NOT device attestation and NOT an installation aid. Proves the split-new
resource choice cannot protect installed EXITFIX when old resource cleanup
targets that path. Original full paired E11 updater ALSO remains NO-GO.
No COM/USB, no filesystem writes, no firmware operations.
"""
from __future__ import annotations

import argparse
from pathlib import Path

EVIDENCE = (
    Path(__file__).resolve().parents[1] /
    "docs/evidence/V1_8_E11_LIVE_OLD_MANIFEST_OPERATOR_2026-10-17.txt"
)
NUMERIC_FIELDS = (
    "old_manifest_resource_files",
    "old_manifest_directories",
    "old_manifest_metadata_lines",
    "old_cleanup_labmate_data_files",
    "old_cleanup_non_labmate_apps_data_files",
    "old_cleanup_app_fap_files",
    "manifest_total_records",
)
FLAGS = {
    "old_cleanup_lists_installed_labmate_fap": {"YES", "NO"},
    "old_cleanup_lists_apps_tools_parent": {"YES", "NO"},
    "current_installed_manifest_provenance": {"READ_FROM_DEVICE_NOT_AUTHENTICATED"},
    "old_resource_cleanup_behavior": {"REMOVES_OLD_MANIFEST_FILE_ENTRIES"},
    "split_new_bundle_excludes_labmate_fap": {"YES_REVIEW_ONLY"},
    "split_updater_guarantees_exitfix_survival": {"NO"},
    "exact_prior_firmware_restore_tested": {"NO"},
    "trial_write_authorized": {"NO"},
    "live_manifest_readback_md5_screen": {"MATCH"},
}
TRAILERS = (
    "E11 OLD RESOURCE CLEANUP SCOPE AUDIT PASS - FIRMWARE TRIAL NO-GO",
    "E11 RESOURCE MANIFEST CHECK PASS - NO FLASH",
)


def analyze_report(text: str) -> dict[str, str]:
    """Validate source-summary consistency; no full resource manifest is stored."""
    lines = [
        l.strip() for l in text.splitlines()
        if l.strip() and not l.lstrip().startswith("#")
    ]
    if len(lines) != len(NUMERIC_FIELDS) + len(FLAGS) + len(TRAILERS):
        raise ValueError("incomplete or unexpected real-device summary")
    if tuple(lines[-2:]) != TRAILERS:
        raise ValueError("NO-GO source audit terminal markers missing")
    fields: dict[str, str] = {}
    for line in lines[:-2]:
        key, sep, value = line.partition(": ")
        if sep != ": " or key in fields or not key or not value:
            raise ValueError("ambiguous audit field")
        fields[key] = value
    if set(fields) != set(NUMERIC_FIELDS) | set(FLAGS):
        raise ValueError("wrong or incomplete audit field set")
    for key in NUMERIC_FIELDS:
        value = fields[key]
        if not value.isascii() or not value.isdecimal() or int(value) > 30000:
            raise ValueError("invalid resource Manifest count")
    for key, expected in FLAGS.items():
        if fields[key] not in expected:
            raise ValueError("unexpected audit provenance/permission/flag")
    numeric = {key: int(fields[key]) for key in NUMERIC_FIELDS}
    if (numeric["old_manifest_resource_files"] +
        numeric["old_manifest_directories"] +
        numeric["old_manifest_metadata_lines"] != numeric["manifest_total_records"]):
        raise ValueError("old manifest record count mismatch")
    if numeric["old_manifest_metadata_lines"] != 2:
        raise ValueError("wrong Manifest metadata count")
    if (numeric["old_cleanup_non_labmate_apps_data_files"] >
        numeric["old_manifest_resource_files"] or
        numeric["old_cleanup_app_fap_files"] > numeric["old_manifest_resource_files"]):
        raise ValueError("subtree counts exceed old manifest files")
    # Identifies CLEANUP EXPOSURE, not proven removal: no updater has run.
    old_fap_is_target = fields["old_cleanup_lists_installed_labmate_fap"] == "YES"
    outcome = (
        "REJECTED_OLD_MANIFEST_WOULD_REMOVE_INSTALLED_FAP"
        if old_fap_is_target else
        "NOT_PROVEN_SAFE_DO_NOT_USE_AS_TRIAL"
    )
    return {
        "evidence_origin": "OPERATOR_REPORTED_REAL_COM7_READ_ONLY_MD5_SCREEN",
        "old_manifest_file_records": fields["old_manifest_resource_files"],
        "old_manifest_total_records": fields["manifest_total_records"],
        "old_manifest_explicitly_lists_labmate_fap": "YES" if old_fap_is_target else "NO",
        "old_manifest_lists_labmate_persistent_data_files": fields["old_cleanup_labmate_data_files"],
        "new_split_resource_bundle_contains_labmate_fap": "NO",
        "split_review_as_exitfix_preserving_trial": outcome,
        "original_full_updater_install_approved": "NO",
        "physical_e11_acceptance_completed": "NO",
        "firmware_trial_authorized": "NO",
        "device_writes_performed": "NO",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence", type=Path, default=EVIDENCE,
        help="offline operator-report summary; NEVER raw private Manifest"
    )
    args = parser.parse_args()
    try:
        result = analyze_report(args.evidence.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        parser.exit(1, "E11 SPLIT TRIAL GATE EVIDENCE REFUSED - NO FLASH: " + str(exc) + "\n")
    for field, value in result.items():
        print(field + ": " + value)
    print("E11 SPLIT REVIEW TRIAL GATE AUDIT PASS - INSTALLATION REJECTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
