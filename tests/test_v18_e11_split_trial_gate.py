#!/usr/bin/env python3
"""Never convert operator's old-Manifest risk evidence into flash approval."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_v18_e11_split_trial_gate import EVIDENCE, analyze_report


class E11SplitSafetyGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real_summary = EVIDENCE.read_text(encoding="utf-8")

    def test_actual_operator_report_rejects_fap_split_preservation(self):
        r = analyze_report(self.real_summary)
        self.assertEqual(r["evidence_origin"],
                         "OPERATOR_REPORTED_REAL_COM7_READ_ONLY_MD5_SCREEN")
        self.assertEqual(r["old_manifest_explicitly_lists_labmate_fap"], "YES")
        self.assertEqual(r["old_manifest_file_records"], "2114")
        self.assertEqual(r["old_manifest_total_records"], "2281")
        self.assertEqual(r["old_manifest_lists_labmate_persistent_data_files"], "0")
        self.assertEqual(r["new_split_resource_bundle_contains_labmate_fap"], "NO")
        self.assertEqual(
            r["split_review_as_exitfix_preserving_trial"],
            "REJECTED_OLD_MANIFEST_WOULD_REMOVE_INSTALLED_FAP"
        )
        self.assertEqual(r["original_full_updater_install_approved"], "NO")
        self.assertEqual(r["firmware_trial_authorized"], "NO")

    def test_even_if_old_manifest_did_not_list_fap_no_go(self):
        simulated = self.real_summary.replace(
            "old_cleanup_lists_installed_labmate_fap: YES",
            "old_cleanup_lists_installed_labmate_fap: NO",
        )
        result = analyze_report(simulated)
        self.assertEqual(result["split_review_as_exitfix_preserving_trial"],
                         "NOT_PROVEN_SAFE_DO_NOT_USE_AS_TRIAL")
        self.assertEqual(result["firmware_trial_authorized"], "NO")

    def test_missing_fap_field_fails_closed(self):
        source = self.real_summary.replace(
            "old_cleanup_lists_installed_labmate_fap: YES\n", "")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            analyze_report(source)

    def test_disallow_upgrade_permission_in_evidence(self):
        for before, after in (
            ("trial_write_authorized: NO", "trial_write_authorized: YES"),
            ("exact_prior_firmware_restore_tested: NO", "exact_prior_firmware_restore_tested: YES"),
            ("live_manifest_readback_md5_screen: MATCH", "live_manifest_readback_md5_screen: MISMATCH"),
            ("split_new_bundle_excludes_labmate_fap: YES_REVIEW_ONLY", "split_new_bundle_excludes_labmate_fap: NO"),
        ):
            with self.subTest(field=before), self.assertRaisesRegex(ValueError, "unexpected"):
                analyze_report(self.real_summary.replace(before, after))

    def test_record_count_tampering_refused(self):
        for before, after in (
            ("manifest_total_records: 2281", "manifest_total_records: 2280"),
            ("old_manifest_resource_files: 2114", "old_manifest_resource_files: 2115"),
            ("old_manifest_metadata_lines: 2", "old_manifest_metadata_lines: 3"),
            ("old_cleanup_app_fap_files: 268", "old_cleanup_app_fap_files: 30000"),
        ):
            with self.subTest(before=before), self.assertRaises(ValueError):
                analyze_report(self.real_summary.replace(before, after))

    def test_evidence_requires_both_no_flash_terminal_markers(self):
        with self.assertRaisesRegex(ValueError, "terminal markers"):
            analyze_report(self.real_summary.replace(
                "E11 RESOURCE MANIFEST CHECK PASS - NO FLASH",
                "E11 RESOURCE MANIFEST CHECK PASS - INSTALL READY",
            ))

    def test_duplicate_or_extra_fields_refused(self):
        with self.assertRaisesRegex(ValueError, "unexpected"):
            analyze_report(self.real_summary +
                           "old_cleanup_lists_installed_labmate_fap: YES\n")

    def test_strict_operator_report_only_no_private_names(self):
        summary = analyze_report(self.real_summary)
        self.assertNotIn("apps/Tools/", str(summary))
        self.assertNotIn("profiles.bin", str(summary))
        self.assertNotIn("log_0041.csv", str(summary))


if __name__ == "__main__":
    unittest.main()
