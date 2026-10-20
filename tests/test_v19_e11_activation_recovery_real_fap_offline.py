#!/usr/bin/env python3
"""Offline-only fault injection for v1.9 true rename/recovery orchestration."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import simulate_v19_e11_storage_cli_offline as fixture
import review_v19_e11_activation_recovery_offline as m


class E11V19OfflineActivationRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.v19 = b"ACTUAL_19_SCHEMA" * 16
        self.v18 = b"KNOWN_V18_FINAL" * 12
        self.legacy = b"PREVIOUS_E11_DEV" * 8
        digest = lambda b: hashlib.sha256(b).hexdigest()
        fixes = [
            (m, "V19_SIZE", len(self.v19)), (m, "V19_SHA", digest(self.v19)),
            (m, "V18_SIZE", len(self.v18)), (m, "V18_SHA", digest(self.v18)),
            (m, "LEGACY_SIZE", len(self.legacy)), (m, "LEGACY_SHA", digest(self.legacy)),
            (fixture, "V18_SIZE", len(self.v18)), (fixture, "V18_SHA", digest(self.v18)),
            (fixture, "LEGACY_SIZE", len(self.legacy)), (fixture, "LEGACY_SHA", digest(self.legacy)),
            (fixture, "RENAMES", frozenset(m.FORWARD | m.BACKWARD)),
        ]
        for obj, name, value in fixes:
            instance = patch.object(obj, name, value)
            instance.start()
            self.addCleanup(instance.stop)
        self.expected = patch.object(m, "EXPECTED", {
            m.ACTIVE: (len(self.v18), digest(self.v18)),
            m.NEW: (len(self.v19), digest(self.v19)),
            m.CURRENT_BACKUP: (len(self.v18), digest(self.v18)),
            m.LEGACY_BACKUP: (len(self.legacy), digest(self.legacy)),
            m.FAILED_V19_BACKUP: (len(self.v19), digest(self.v19)),
        })
        self.expected.start()
        self.addCleanup(self.expected.stop)

    def mock(self, *, stage=True, faults=()):
        client = fixture.FakeCLI(self.v18, self.legacy, set(faults))
        if stage:
            client.fs[m.NEW] = self.v19
        return client

    def activated(self):
        cli = self.mock()
        m.promote_two_renames(cli, self.v19, self.v18, self.legacy)
        return cli

    def test_successful_two_step_exact_promotion_preserves_three_artifacts(self):
        d = self.mock()
        report = m.promote_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(report["offline_activation"], "PASS_TWO_RENAMES")
        self.assertEqual(d.rename_count, 2)
        self.assertEqual(d.fs[m.ACTIVE], self.v19)
        self.assertEqual(d.fs[m.CURRENT_BACKUP], self.v18)
        self.assertEqual(d.fs[m.LEGACY_BACKUP], self.legacy)
        self.assertNotIn(m.NEW, d.fs)
        self.assertEqual(d.chunk_count, 0)

    def test_successful_manual_rollback_preserves_both_old_and_new(self):
        d = self.activated()
        m.rollback_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 4)
        self.assertEqual(d.fs[m.ACTIVE], self.v18)
        self.assertEqual(d.fs[m.FAILED_V19_BACKUP], self.v19)
        self.assertEqual(d.fs[m.LEGACY_BACKUP], self.legacy)
        self.assertNotIn(m.CURRENT_BACKUP, d.fs)
        self.assertEqual(d.chunk_count, 0)

    def test_interrupted_first_rename_manual_recovery_returns_to_staged(self):
        d = self.mock()
        m.rename_once(d, m.ACTIVE, m.CURRENT_BACKUP, m.FORWARD)
        self.assertNotIn(m.ACTIVE, d.fs)
        m.recover_interrupted_first_rename(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 2)
        self.assertEqual(d.fs[m.ACTIVE], self.v18)
        self.assertEqual(d.fs[m.NEW], self.v19)
        self.assertNotIn(m.CURRENT_BACKUP, d.fs)

    def test_stage_missing_rejected_before_rename(self):
        d = self.mock(stage=False)
        with self.assertRaises(ValueError):
            m.promote_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 0)

    def test_wrong_size_stage_rejected_before_rename(self):
        d = self.mock()
        d.fs[m.NEW] = self.v19[:-1]
        with self.assertRaises(ValueError):
            m.promote_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 0)

    def test_stage_md5_corruption_rejected_before_rename(self):
        d = self.mock(faults={"stage-md5-bad"})
        with self.assertRaisesRegex(ValueError, "checksum"):
            m.promote_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 0)

    def test_stage_binary_readback_corruption_rejected(self):
        d = self.mock(faults={"stage-readback-corrupt"})
        with self.assertRaisesRegex(ValueError, "binary readback"):
            m.promote_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 0)

    def test_occupied_final_v18_backup_rejected(self):
        d = self.mock()
        d.fs[m.CURRENT_BACKUP] = self.v18
        with self.assertRaisesRegex(ValueError, "not absent"):
            m.promote_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 0)

    def test_occupied_failed_v19_backup_rejected(self):
        d = self.mock()
        d.fs[m.FAILED_V19_BACKUP] = self.v19
        with self.assertRaisesRegex(ValueError, "not absent"):
            m.promote_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 0)

    def test_original_v18_mutation_refused(self):
        d = self.mock()
        d.fs[m.ACTIVE] = b"?" + self.v18[1:]
        with self.assertRaisesRegex(ValueError, "checksum"):
            m.promote_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 0)

    def test_historical_e11_mutation_refused(self):
        d = self.mock()
        d.fs[m.LEGACY_BACKUP] = self.legacy[:-1] + b"?"
        with self.assertRaisesRegex(ValueError, "checksum"):
            m.promote_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 0)

    def test_first_rename_ambiguous_reply_leaves_gap_no_auto_retry(self):
        d = self.mock(faults={"rename-reply-fail"})
        with self.assertRaisesRegex(ValueError, "ambiguous rename outcome"):
            m.promote_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 1)
        self.assertNotIn(m.ACTIVE, d.fs)
        self.assertEqual(d.fs[m.CURRENT_BACKUP], self.v18)
        self.assertEqual(d.fs[m.NEW], self.v19)

    def test_second_rename_ambiguous_reply_never_reports_success(self):
        d = self.mock(faults={"rename-reply-fail-second"})
        with self.assertRaisesRegex(ValueError, "ambiguous rename outcome"):
            m.promote_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 2)
        self.assertEqual(d.fs[m.ACTIVE], self.v19)
        self.assertEqual(d.fs[m.CURRENT_BACKUP], self.v18)

    def test_unsafe_rename_pair_rejected_pre_command(self):
        d = self.mock()
        with self.assertRaisesRegex(ValueError, "not strictly allowlisted"):
            m.rename_once(d, m.LEGACY_BACKUP, m.ACTIVE, m.FORWARD)
        self.assertEqual(d.rename_count, 0)

    def test_unexpected_stat_echo_aborts_before_rename(self):
        d = self.mock(faults={"echo-fail"})
        # FakeCLI intentionally raises at the transport boundary BEFORE the
        # higher-level stat parser can produce its own echo-error message.
        with self.assertRaisesRegex(ValueError, "simulated CLI command echo disagreement"):
            m.promote_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 0)
        self.assertEqual(d.chunk_count, 0)
        self.assertEqual(len(d.commands), 1)
        self.assertTrue(d.commands[0].startswith("storage stat "))
        self.assertEqual(d.fs[m.ACTIVE], self.v18)
        self.assertEqual(d.fs[m.NEW], self.v19)
        self.assertEqual(d.fs[m.LEGACY_BACKUP], self.legacy)

    def test_repeated_activation_refused_with_no_new_rename(self):
        d = self.activated()
        with self.assertRaises(ValueError):
            m.promote_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 2)

    def test_rollback_from_non_activated_state_refused(self):
        d = self.mock()
        with self.assertRaises(ValueError):
            m.rollback_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 0)

    def test_recovery_from_non_gap_state_refused(self):
        d = self.mock()
        with self.assertRaises(ValueError):
            m.recover_interrupted_first_rename(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 0)

    def test_rollback_occupied_failed_backup_refused_without_rename(self):
        d = self.activated()
        d.fs[m.FAILED_V19_BACKUP] = self.v19
        with self.assertRaisesRegex(ValueError, "not absent"):
            m.rollback_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 2)

    def test_rollback_first_move_ambiguous_stops_and_preserves_v18_backup(self):
        d = self.activated()
        d.faults.add("rename-reply-fail")
        with self.assertRaisesRegex(ValueError, "ambiguous rename outcome"):
            m.rollback_two_renames(d, self.v19, self.v18, self.legacy)
        self.assertEqual(d.rename_count, 3)
        self.assertNotIn(m.ACTIVE, d.fs)
        self.assertEqual(d.fs[m.CURRENT_BACKUP], self.v18)
        self.assertEqual(d.fs[m.FAILED_V19_BACKUP], self.v19)

    def test_bad_fap_input_blocks_all_renames(self):
        d = self.mock()
        with self.assertRaisesRegex(ValueError, "local FAP input"):
            m.promote_two_renames(d, self.v19[:-1], self.v18, self.legacy)
        self.assertEqual(d.rename_count, 0)

    def test_no_device_or_pc_connection_possible_from_main(self):
        text = Path(m.__file__).read_text("utf-8")
        for forbidden in ("import serial", "FlipperStorage(", "storage write_chunk ",
                          "storage remove ", "storage mkdir ", "storage format ",
                          "--port", "--apply", "shutil", "open(", ".write_bytes("):
            self.assertNotIn(forbidden, text)
        self.assertIn("fixture.FakeCLI(", text)


if __name__ == "__main__":
    unittest.main()
