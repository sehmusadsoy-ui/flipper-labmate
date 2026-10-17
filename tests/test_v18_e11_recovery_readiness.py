#!/usr/bin/env python3
"""Synthetic recovery risk decisions: no device, no installs, no state writes."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audit_v18_e11_recovery_readiness import (
    audit, recorded_evidence, SUPPORTED_BASE,
    OFFICIAL_FALLBACK_RELEASE
)
from preflight_v18_e11_local import INSTALLED_EXITFIX, ROLLBACK, ARTIFACTS


class E11RecoveryReadinessTest(unittest.TestCase):
    def setUp(self):
        self.e = recorded_evidence()

    def test_current_actual_evidence_fails_closed_with_honest_fallback_label(self):
        r = audit(self.e)
        self.assertEqual(r["exact_prior_firmware_recovery"], "NOT_PROVEN")
        self.assertEqual(r["known_official_release_fallback"],
                         "FILE_VERIFIED_BOOT_UNTESTED")
        self.assertEqual(r["firmware_trial_decision"], "NO_GO")
        self.assertEqual(r["device_changes_performed"], "NO")
        self.assertEqual(r["new_trial_owner_permission"], "NO")
        self.assertEqual(r["nominal_channel_or_dirty_mismatch"], "YES")

    def test_preserved_exitfix_is_exact_known_fap_not_stable(self):
        r = audit(self.e)
        self.assertEqual(self.e.installed_fap_sha256, INSTALLED_EXITFIX)
        self.assertEqual(self.e.available_stable_fap_sha256,
                         ROLLBACK["labmate-v18-stable.fap"])
        self.assertEqual(self.e.candidate_fap_sha256, ARTIFACTS["labmate.fap"])
        self.assertEqual(r["preserved_current_exitfix_fap_identity"], "MATCH")
        self.assertEqual(r["stable_fap_is_current_exitfix"], "NO")
        self.assertEqual(r["candidate_fap_is_current_exitfix"], "NO")

    def test_nominal_base_not_exact_installed_firmware_hash(self):
        self.assertEqual(self.e.current_base_commit, SUPPORTED_BASE)
        self.assertEqual(self.e.firmware_recovery_target,
                         OFFICIAL_FALLBACK_RELEASE)
        self.assertIsNone(self.e.installed_firmware_sha256)

    def test_mutated_rollback_digest_refused(self):
        with self.assertRaisesRegex(ValueError, "official 012"):
            audit(replace(self.e, rollback_tgz_sha256="a" * 64))

    def test_missing_or_malformed_hash_refused(self):
        for field in ("installed_fap_sha256", "preserved_fap_copy_sha256",
                      "available_stable_fap_sha256", "candidate_fap_sha256"):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "SHA256"):
                audit(replace(self.e, **{field: "not-a-digest"}))
        with self.assertRaisesRegex(ValueError, "installed firmware image hash"):
            audit(replace(self.e, installed_firmware_sha256="short"))

    def test_older_stable_fap_not_same_as_installed_exitfix(self):
        r = audit(replace(self.e, preserved_fap_copy_sha256="f" * 64))
        self.assertEqual(r["preserved_current_exitfix_fap_identity"], "MISMATCH")
        self.assertEqual(r["firmware_trial_decision"], "NO_GO")

    def test_even_owner_approval_alone_cannot_turn_review_into_flashable(self):
        r = audit(replace(self.e, explicit_new_trial_authorized=True))
        self.assertEqual(r["new_trial_owner_permission"], "YES")
        self.assertEqual(r["firmware_trial_decision"], "NO_GO")

    def test_boot_rehearsal_alone_does_not_prove_exact_firmware(self):
        r = audit(replace(self.e, rollback_boot_rehearsed=True))
        self.assertEqual(r["rollback_boot_on_device_rehearsed"], "YES")
        self.assertEqual(r["exact_prior_firmware_recovery"], "NOT_PROVEN")
        self.assertEqual(r["firmware_trial_decision"], "NO_GO")

    def test_optional_full_sd_backup_is_separate_from_radio_rollback(self):
        r = audit(replace(self.e, whole_sd_preserved=True))
        self.assertEqual(r["whole_sd_contents_preserved"], "YES")
        self.assertEqual(r["firmware_trial_decision"], "NO_GO")

    def test_known_image_hash_without_recovery_image_not_enough(self):
        r = audit(replace(self.e, installed_firmware_sha256="a" * 64))
        self.assertEqual(r["exact_prior_firmware_recovery"], "NOT_PROVEN")
        self.assertEqual(r["exact_prior_firmware_blocker"],
                         "PRIOR_FULL_RESTORABLE_FW_IMAGE_NOT_INDEPENDENTLY_VERIFIED")

    def test_wrong_candidate_label_refused(self):
        with self.assertRaisesRegex(ValueError, "blocked"):
            audit(replace(self.e, candidate_label="READY TO FLASH"))

    def test_wrong_base_commit_refused(self):
        with self.assertRaisesRegex(ValueError, "nominal"):
            audit(replace(self.e, current_base_commit="d3f89dfe"))

    def test_missing_historical_or_current_labmate_copy_refused(self):
        for kw in ("historical_labmate_backup_files", "current_labmate_snapshot_files"):
            with self.subTest(kw=kw), self.assertRaisesRegex(ValueError, "both LabMate"):
                audit(replace(self.e, **{kw: 0}))


if __name__ == "__main__":
    unittest.main()
