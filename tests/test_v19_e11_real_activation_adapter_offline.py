#!/usr/bin/env python3
"""OFFLINE tests of actual separately consent-gated v1.9 activation adapter.

The FakeCLI has no real serial hardware. All mock native firmware attestation
and poststage device resource attestations in this file are ONLY synthetic.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import activate_v19_e11_once_review_only as a
import review_v19_e11_activation_recovery_offline as model
import simulate_v19_e11_storage_cli_offline as fake


class RealActivationAdapterOfflineTest(unittest.TestCase):
    def setUp(self):
        self.v18 = b"ACTUAL_PREVIOUS_FINAL" * 10
        self.v19 = b"ACTUAL_NEXT_STAGED" * 12
        self.legacy = b"ACTUAL_E11_BACKUP" * 8
        sha = lambda b: hashlib.sha256(b).hexdigest()
        for module in (model, fake):
            for name, blob in (("V18", self.v18), ("V19", self.v19),
                               ("LEGACY", self.legacy)):
                for suffix, val in (("SIZE", len(blob)), ("SHA", sha(blob))):
                    key = name + "_" + suffix
                    if hasattr(module, key):
                        obj = patch.object(module, key, val)
                        obj.start()
                        self.addCleanup(obj.stop)
        obj = patch.object(model, "EXPECTED", {
            model.ACTIVE: (len(self.v18), sha(self.v18)),
            model.NEW: (len(self.v19), sha(self.v19)),
            model.CURRENT_BACKUP: (len(self.v18), sha(self.v18)),
            model.LEGACY_BACKUP: (len(self.legacy), sha(self.legacy)),
            model.FAILED_V19_BACKUP: (len(self.v19), sha(self.v19)),
        })
        obj.start()
        self.addCleanup(obj.stop)
        obj = patch.object(fake, "RENAMES", frozenset(model.FORWARD))
        obj.start()
        self.addCleanup(obj.stop)
        obj = patch.object(a, "attest_poststage",
                           return_value={"state": "STAGED_V19_NONAPP_ACTIVE_V18"})
        obj.start()
        self.addCleanup(obj.stop)
        obj = patch.object(a, "identity_resources_ro")
        obj.start()
        self.addCleanup(obj.stop)

    def device(self, *, faults=(), stage=True):
        d = fake.FakeCLI(self.v18, self.legacy, set(faults))
        if stage:
            d.fs[model.NEW] = self.v19
        return d

    def run_live_path(self, d):
        return a.activate_on_client_once(d, self.v19, self.v18, self.legacy,
                                         {}, {}, "test-md5")

    def test_two_exact_same_directory_moves_then_independent_stop(self):
        d = self.device()
        report = self.run_live_path(d)
        self.assertEqual(report["v19_file_promotion"], "PASS_TWO_NONATOMIC_RENAMES")
        self.assertEqual(report["next_action"], "STOP_FOR_INDEPENDENT_READ_ONLY_ACTIVATED_STATE_SCAN")
        self.assertEqual(d.fs[model.ACTIVE], self.v19)
        self.assertEqual(d.fs[model.CURRENT_BACKUP], self.v18)
        self.assertEqual(d.fs[model.LEGACY_BACKUP], self.legacy)
        self.assertNotIn(model.NEW, d.fs)
        self.assertEqual(d.rename_count, 2)
        self.assertEqual(d.chunk_count, 0)

    def test_missing_stage_fails_before_mutating(self):
        d = self.device(stage=False)
        with self.assertRaises(ValueError):
            self.run_live_path(d)
        self.assertEqual(d.rename_count, 0)

    def test_mismatched_staged_md5_fails_before_mutating(self):
        d = self.device(faults={"stage-md5-bad"})
        with self.assertRaises(ValueError):
            self.run_live_path(d)
        self.assertEqual(d.rename_count, 0)

    def test_occupied_final_backup_fails_before_mutating(self):
        d = self.device()
        d.fs[model.CURRENT_BACKUP] = self.v18
        with self.assertRaises(ValueError):
            self.run_live_path(d)
        self.assertEqual(d.rename_count, 0)

    def test_occupied_failed_backup_fails_before_mutating(self):
        d = self.device()
        d.fs[model.FAILED_V19_BACKUP] = self.v19
        with self.assertRaises(ValueError):
            self.run_live_path(d)
        self.assertEqual(d.rename_count, 0)

    def test_native_resource_drift_does_not_rename(self):
        d = self.device()
        with patch.object(a, "identity_resources_ro", side_effect=ValueError("resource drift")):
            with self.assertRaisesRegex(ValueError, "resource drift"):
                self.run_live_path(d)
        self.assertEqual(d.rename_count, 0)

    def test_failed_real_poststage_attestation_no_mutation(self):
        d = self.device()
        with patch.object(a, "attest_poststage", side_effect=ValueError("DRIFT")):
            with self.assertRaises(ValueError):
                self.run_live_path(d)
        self.assertEqual(d.rename_count, 0)

    def test_wrong_state_from_prewrite_check_no_mutation(self):
        d = self.device()
        with patch.object(a, "attest_poststage", return_value={"state": "WRONG"}):
            with self.assertRaisesRegex(ValueError, "pre-activation state"):
                self.run_live_path(d)
        self.assertEqual(d.rename_count, 0)

    def test_first_rename_ambiguous_leaves_actual_gap_and_stops(self):
        d = self.device(faults={"rename-reply-fail"})
        with self.assertRaisesRegex(ValueError, "ambiguous rename outcome"):
            self.run_live_path(d)
        self.assertEqual(d.rename_count, 1)
        self.assertNotIn(model.ACTIVE, d.fs)
        self.assertEqual(d.fs[model.CURRENT_BACKUP], self.v18)
        self.assertEqual(d.fs[model.NEW], self.v19)

    def test_second_rename_ambiguous_stops_and_does_not_repeat(self):
        d = self.device(faults={"rename-reply-fail-second"})
        with self.assertRaisesRegex(ValueError, "ambiguous rename outcome"):
            self.run_live_path(d)
        self.assertEqual(d.rename_count, 2)
        self.assertEqual(d.fs[model.ACTIVE], self.v19)
        self.assertEqual(d.fs[model.CURRENT_BACKUP], self.v18)

    def test_old_fap_size_drift_fails_before_rename(self):
        d = self.device()
        d.fs[model.ACTIVE] = self.v18[:-1]
        with self.assertRaises(ValueError):
            self.run_live_path(d)
        self.assertEqual(d.rename_count, 0)

    def test_historical_e11_backup_drift_fails_before_rename(self):
        d = self.device()
        d.fs[model.LEGACY_BACKUP] = self.legacy[:-1] + b"X"
        with self.assertRaises(ValueError):
            self.run_live_path(d)
        self.assertEqual(d.rename_count, 0)

    def test_real_adapter_refuses_replay_if_already_promoted(self):
        d = self.device()
        self.run_live_path(d)
        with self.assertRaises(ValueError):
            self.run_live_path(d)
        self.assertEqual(d.rename_count, 2)

    def test_missing_independent_activation_token_no_com_access(self):
        argv = ["script", "--port", "COM7", "--momentum-scripts", "/missing",
                "--old-candidate", "/missing", "--saved-old-fap-backup", "/missing",
                "--final-v18-fap", "/missing", "--active-v18-backup", "/missing",
                "--data-snapshot", "/missing", "--candidate", "/missing",
                "--approve-two-renames", "STAGE_ONLY_APPROVAL_IS_NOT_SUFFICIENT",
                "--accept-unverified-abi-risk", a.ABI_RISK]
        with patch.object(sys, "argv", argv):
            self.assertEqual(a.main(), 1)

    def test_missing_native_abi_risk_acknowledgement_no_com_access(self):
        argv = ["script", "--port", "COM7", "--momentum-scripts", "/missing",
                "--old-candidate", "/missing", "--saved-old-fap-backup", "/missing",
                "--final-v18-fap", "/missing", "--active-v18-backup", "/missing",
                "--data-snapshot", "/missing", "--candidate", "/missing",
                "--approve-two-renames", a.AUTH,
                "--accept-unverified-abi-risk", "NOT_ACCEPTED"]
        with patch.object(sys, "argv", argv):
            self.assertEqual(a.main(), 1)

    def test_only_the_two_exact_activation_moves_have_live_permission(self):
        self.assertEqual(model.FORWARD, frozenset((
            ("/ext/apps/Tools/labmate.fap",
             "/ext/apps/Tools/labmate.v18-final-before-v19.bak"),
            ("/ext/apps/Tools/labmate.v19-new-stage",
             "/ext/apps/Tools/labmate.fap"))))

    def test_no_automatic_restore_delete_upload_flash(self):
        source = Path(a.__file__).read_text("utf-8")
        self.assertNotIn("storage remove ", source)
        self.assertNotIn("storage write_chunk ", source)
        self.assertNotIn("storage format ", source)
        self.assertNotIn("rollback_two_renames(", source)
        self.assertNotIn("recover_interrupted_first_rename(", source)


if __name__ == "__main__":
    unittest.main()
