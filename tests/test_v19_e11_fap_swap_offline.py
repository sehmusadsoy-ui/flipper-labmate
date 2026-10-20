#!/usr/bin/env python3
"""Synthetic v1.9 E11 FAP stage/two-rename simulator fault-injection tests.

Pure-memory virtual snapshots. Not a Flipper COM/USB or real FAT filesystem test.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import simulate_v19_e11_fap_swap_offline as m


class OfflineV19SwapTest(unittest.TestCase):
    def setUp(self):
        self.v18 = b"final-v1.8"
        self.legacy = b"legacy-E11"
        self.new = b"new-v1.9"
        values = {
            "V18_SHA": m.sha256(self.v18), "V18_SIZE": len(self.v18),
            "LEGACY_SHA": m.sha256(self.legacy), "LEGACY_SIZE": len(self.legacy),
            "V19_SHA": m.sha256(self.new), "V19_SIZE": len(self.new),
            "CHUNK": 3,
        }
        for k, val in values.items():
            patcher = patch.object(m, k, val)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.initial = m.initial_state(self.v18, self.legacy)

    def test_original_v18_active(self):
        self.assertEqual(m.state_of(self.initial), "ORIGINAL_V18_ACTIVE")

    def test_clean_staging_never_displaces_v18(self):
        s = m.stage_only(self.initial, self.new)
        self.assertEqual(m.state_of(s), "V19_STAGED_V18_ACTIVE")
        self.assertEqual(s.active, self.v18)
        self.assertEqual(s.legacy_backup, self.legacy)

    def test_first_rename_preserves_v18_in_separate_new_backup(self):
        staged = m.stage_only(self.initial, self.new)
        between = m.first_rename(staged)
        self.assertIsNone(between.active)
        self.assertEqual(between.v18_backup, self.v18)
        self.assertEqual(between.legacy_backup, self.legacy)
        self.assertEqual(between.stage, self.new)
        self.assertEqual(m.state_of(between), "BETWEEN_RENAMES_ACTIVE_ABSENT_STOP")

    def test_second_rename_only_after_first(self):
        end = m.second_rename(m.first_rename(m.stage_only(self.initial, self.new)))
        self.assertEqual(end.active, self.new)
        self.assertIsNone(end.stage)
        self.assertEqual(end.v18_backup, self.v18)
        self.assertEqual(end.legacy_backup, self.legacy)
        self.assertEqual(m.state_of(end), "V19_ACTIVE_WITH_V18_BACKUP")

    def test_virtual_full_protocol_and_fault_cases(self):
        result = m.run_virtual_scenarios(self.v18, self.legacy, self.new)
        self.assertEqual(len(result), 9)
        self.assertEqual(result["NO_BLIND_STAGE_RETRY"], "PASS")

    def test_bad_ready_never_writes_even_virtual_stage(self):
        with self.assertRaises(m.TrialStop) as caught:
            m.stage_only(self.initial, self.new, fault="bad-ready")
        self.assertEqual(caught.exception.state, self.initial)

    def test_partial_first_chunk_leaves_v18_active_and_partial(self):
        with self.assertRaises(m.TrialStop) as caught:
            m.stage_only(self.initial, self.new, fault="short-first-chunk")
        state = caught.exception.state
        self.assertEqual(state.active, self.v18)
        self.assertIsNone(state.v18_backup)
        self.assertEqual(m.state_of(state), "PARTIAL_STAGE_V18_ACTIVE_STOP")

    def test_staged_hash_failure_refuses_activation(self):
        with self.assertRaises(m.TrialStop) as caught:
            m.stage_only(self.initial, self.new, fault="last-byte-corrupt")
        with self.assertRaises(m.TrialStop):
            m.first_rename(caught.exception.state)

    def test_no_blind_retry_when_partial_stage_exists(self):
        partial = replace(self.initial, stage=b"short")
        with self.assertRaises(m.TrialStop):
            m.stage_only(partial, self.new)

    def test_no_overwrite_if_new_final_backup_exists(self):
        occupied = replace(self.initial, v18_backup=self.v18)
        self.assertEqual(m.state_of(occupied), "UNKNOWN_STOP")
        with self.assertRaises(m.TrialStop):
            m.stage_only(occupied, self.new)

    def test_legacy_backup_mutation_stops_all(self):
        altered = replace(self.initial, legacy_backup=b"changed")
        with self.assertRaises(m.TrialStop):
            m.stage_only(altered, self.new)

    def test_original_app_missing_blocks_first_rename(self):
        no_app = replace(self.initial, active=None)
        with self.assertRaises(m.TrialStop):
            m.first_rename(no_app)

    def test_first_rename_before_complete_stage_blocked(self):
        with self.assertRaises(m.TrialStop):
            m.first_rename(self.initial)

    def test_second_rename_before_first_is_blocked(self):
        staged = m.stage_only(self.initial, self.new)
        with self.assertRaises(m.TrialStop):
            m.second_rename(staged)

    def test_manual_intervention_required_after_first_rename(self):
        stage = m.stage_only(self.initial, self.new)
        between = m.first_rename(stage)
        self.assertIsNone(between.active)
        with self.assertRaises(m.TrialStop):
            m.stage_only(between, self.new)
        self.assertEqual(between.v18_backup, self.v18)

    def test_manual_recovery_from_interrupted_first_rename_virtual(self):
        between = m.first_rename(m.stage_only(self.initial, self.new))
        recovered = m.manual_recover_first_rename_interruption(between)
        self.assertEqual(m.state_of(recovered), "V19_STAGED_V18_ACTIVE")
        self.assertEqual(recovered.active, self.v18)
        self.assertEqual(recovered.stage, self.new)
        self.assertEqual(recovered.legacy_backup, self.legacy)

    def test_manual_virtual_rollback_both_safe_moves(self):
        final = m.second_rename(m.first_rename(m.stage_only(self.initial, self.new)))
        rollback_gap = m.manual_rollback_first_rename(final)
        self.assertEqual(m.state_of(rollback_gap), "MANUAL_ROLLBACK_BETWEEN_RENAMES_STOP")
        self.assertIsNone(rollback_gap.active)
        restored = m.manual_rollback_second_rename(rollback_gap)
        self.assertEqual(m.state_of(restored), "ROLLED_BACK_TO_V18_V19_PRESERVED")
        self.assertEqual(restored.active, self.v18)
        self.assertEqual(restored.failed_v19_backup, self.new)
        self.assertEqual(restored.legacy_backup, self.legacy)

    def test_no_manual_rollback_when_failed_v19_backup_occupied(self):
        final = m.second_rename(m.first_rename(m.stage_only(self.initial, self.new)))
        collision = replace(final, failed_v19_backup=self.new)
        with self.assertRaises(m.TrialStop):
            m.manual_rollback_first_rename(collision)

    def test_no_second_manual_rollback_without_first(self):
        final = m.second_rename(m.first_rename(m.stage_only(self.initial, self.new)))
        with self.assertRaises(m.TrialStop):
            m.manual_rollback_second_rename(final)

    def test_no_manual_interrupted_recovery_after_fully_promoted(self):
        final = m.second_rename(m.first_rename(m.stage_only(self.initial, self.new)))
        with self.assertRaises(m.TrialStop):
            m.manual_recover_first_rename_interruption(final)

    def test_corrupt_candidate_refused_without_staging(self):
        with self.assertRaises(ValueError):
            m.stage_only(self.initial, b"not-candidate")

    def test_reject_unverified_fap_pc_path(self):
        with tempfile.TemporaryDirectory() as work:
            f = Path(work) / "bad.fap"
            f.write_bytes(b"?" * len(self.new))
            with self.assertRaises(ValueError):
                m.verified_pc_artifact(f, len(self.new), m.V19_SHA)

    def test_reject_missing_pc_file(self):
        with tempfile.TemporaryDirectory() as work:
            with self.assertRaises(ValueError):
                m.verified_pc_artifact(Path(work) / "missing.fap", len(self.new), m.V19_SHA)

    def test_reject_unrecognized_fault_argument(self):
        with self.assertRaises(ValueError):
            m.stage_only(self.initial, self.new, fault="auto-rollback")

    def test_v18_and_legacy_paths_are_distinct(self):
        self.assertEqual(len({m.ACTIVE, m.NEW, m.CURRENT_BACKUP, m.LEGACY_BACKUP, m.FAILED_V19_BACKUP}), 5)
        self.assertIn("/Tools/", m.ACTIVE)
        self.assertIn("/Tools/", m.CURRENT_BACKUP)


if __name__ == "__main__":
    unittest.main()
