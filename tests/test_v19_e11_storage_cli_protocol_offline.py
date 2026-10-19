#!/usr/bin/env python3
"""Only in-memory fake E11 CLI. NO USB/COM/device connection or disk writes.

These assertions are NOT actual Flipper protocol/firmware validation.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import simulate_v19_e11_storage_cli_offline as m


class VirtualCliProtocolTest(unittest.TestCase):
    def setUp(self):
        self.v18 = b"v1.8 final" * 3
        self.legacy = b"E11 original v18dev" * 2
        self.new = b"v19 Scope test FAP bytes" * 1000
        spec = {
            "V18_SIZE": len(self.v18),
            "V18_SHA": m.sha(self.v18),
            "LEGACY_SIZE": len(self.legacy),
            "LEGACY_SHA": m.sha(self.legacy),
            "V19_SIZE": len(self.new),
            "V19_SHA": m.sha(self.new),
        }
        for name, value in spec.items():
            patcher = patch.object(m, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def make(self, *faults):
        return m.FakeCLI(self.v18, self.legacy, set(faults))

    def test_clean_stage_then_two_separate_protected_renames(self):
        cli = self.make()
        m.stage(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.fs[m.ACTIVE], self.v18)
        self.assertEqual(cli.fs[m.NEW], self.new)
        self.assertNotIn(m.CURRENT_BACKUP, cli.fs)
        m.promote(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.rename_count, 2)
        self.assertEqual(cli.fs[m.ACTIVE], self.new)
        self.assertEqual(cli.fs[m.CURRENT_BACKUP], self.v18)
        self.assertEqual(cli.fs[m.LEGACY_BACKUP], self.legacy)
        self.assertNotIn(m.NEW, cli.fs)

    def test_complete_protocol_summary(self):
        result = m.simulate(self.v18, self.legacy, self.new)
        self.assertEqual(result["MOCK_STAGE"], "PASS")
        self.assertEqual(result["MOCK_RENAME_COUNT"], 2)
        self.assertEqual(result["MOCK_CHUNKS"], (len(self.new) + m.MAX_CHUNK - 1) // m.MAX_CHUNK)

    def test_before_stage_active_v18_is_checked_and_preserved(self):
        cli = self.make()
        m.preflight(cli, self.v18, self.legacy)
        self.assertEqual(set(cli.fs), {m.ACTIVE, m.LEGACY_BACKUP})
        self.assertEqual(cli.rename_count, 0)

    def test_bad_ready_stops_before_binary_or_rename(self):
        cli = self.make("bad-ready")
        with self.assertRaises(ValueError):
            m.stage(cli, self.new, self.v18, self.legacy)
        self.assertNotIn(m.NEW, cli.fs)
        self.assertEqual(cli.fs[m.ACTIVE], self.v18)
        self.assertEqual(cli.rename_count, 0)

    def test_bad_command_echo_blocks_stage(self):
        cli = self.make("echo-fail")
        with self.assertRaises(ValueError):
            m.stage(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.fs[m.ACTIVE], self.v18)
        self.assertEqual(cli.rename_count, 0)

    def test_short_write_leaves_partial_stage_and_old_app(self):
        cli = self.make("short-first-chunk")
        with self.assertRaisesRegex(ValueError, "short native write"):
            m.stage(cli, self.new, self.v18, self.legacy)
        self.assertIn(m.NEW, cli.fs)
        self.assertLess(len(cli.fs[m.NEW]), len(self.new))
        self.assertEqual(cli.fs[m.ACTIVE], self.v18)
        self.assertEqual(cli.rename_count, 0)

    def test_unexpected_after_chunk_reply_keeps_v18(self):
        cli = self.make("chunk-tail-fail")
        with self.assertRaises(ValueError):
            m.stage(cli, self.new, self.v18, self.legacy)
        self.assertIn(m.NEW, cli.fs)
        self.assertEqual(cli.fs[m.ACTIVE], self.v18)
        self.assertEqual(cli.rename_count, 0)

    def test_stage_md5_tamper_stops_activation(self):
        cli = self.make("stage-md5-bad")
        with self.assertRaisesRegex(ValueError, "MD5"):
            m.stage(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.fs[m.ACTIVE], self.v18)
        self.assertEqual(cli.rename_count, 0)

    def test_full_stage_readback_corruption_stops(self):
        cli = self.make("stage-readback-corrupt")
        with self.assertRaisesRegex(ValueError, "readback"):
            m.stage(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.fs[m.ACTIVE], self.v18)

    def test_stage_already_occupied_blocks_all_writes(self):
        cli = self.make()
        cli.fs[m.NEW] = b"partial"
        with self.assertRaisesRegex(ValueError, "occupied"):
            m.stage(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.chunk_count, 0)
        self.assertEqual(cli.fs[m.ACTIVE], self.v18)

    def test_v18_recovery_path_occupied_blocks_stage(self):
        cli = self.make()
        cli.fs[m.CURRENT_BACKUP] = self.v18
        with self.assertRaisesRegex(ValueError, "occupied"):
            m.stage(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.chunk_count, 0)

    def test_reserved_failed_new_path_occupied_blocks_stage(self):
        cli = self.make()
        cli.fs[m.FAILED_V19_BACKUP] = b"keep"
        with self.assertRaisesRegex(ValueError, "occupied"):
            m.stage(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.chunk_count, 0)

    def test_legacy_e11_backup_mutation_blocks_stage(self):
        cli = self.make()
        cli.fs[m.LEGACY_BACKUP] = b"bad"
        with self.assertRaises(ValueError):
            m.stage(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.chunk_count, 0)

    def test_active_v18_mutation_blocks_stage(self):
        cli = self.make()
        cli.fs[m.ACTIVE] = b"bad"
        with self.assertRaises(ValueError):
            m.stage(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.chunk_count, 0)

    def test_corrupt_candidate_fap_hash_refused(self):
        cli = self.make()
        wrong = b"?" + self.new[1:]
        with self.assertRaisesRegex(ValueError, "wrong candidate"):
            m.stage(cli, wrong, self.v18, self.legacy)
        self.assertEqual(cli.chunk_count, 0)

    def test_wrong_candidate_size_refused(self):
        cli = self.make()
        with self.assertRaisesRegex(ValueError, "wrong candidate"):
            m.stage(cli, self.new[:-1], self.v18, self.legacy)

    def test_blind_stage_retry_is_refused(self):
        cli = self.make()
        m.stage(cli, self.new, self.v18, self.legacy)
        old_count = cli.chunk_count
        with self.assertRaisesRegex(ValueError, "occupied"):
            m.stage(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.chunk_count, old_count)

    def test_promotion_without_staged_file_is_refused(self):
        cli = self.make()
        with self.assertRaises(ValueError):
            m.promote(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.rename_count, 0)

    def test_new_backup_occupied_after_stage_blocks_rename(self):
        cli = self.make()
        m.stage(cli, self.new, self.v18, self.legacy)
        cli.fs[m.CURRENT_BACKUP] = b"existing"
        with self.assertRaises(ValueError):
            m.promote(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.rename_count, 0)

    def test_stage_mutated_after_complete_stage_blocks_rename(self):
        cli = self.make()
        m.stage(cli, self.new, self.v18, self.legacy)
        cli.fs[m.NEW] = b"changed"
        with self.assertRaises(ValueError):
            m.promote(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.rename_count, 0)

    def test_ambiguous_first_rename_has_backup_but_app_absent_stop(self):
        cli = self.make("rename-reply-fail")
        m.stage(cli, self.new, self.v18, self.legacy)
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            m.promote(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.rename_count, 1)
        self.assertNotIn(m.ACTIVE, cli.fs)
        self.assertEqual(cli.fs[m.CURRENT_BACKUP], self.v18)
        self.assertEqual(cli.fs[m.NEW], self.new)
        self.assertEqual(cli.fs[m.LEGACY_BACKUP], self.legacy)

    def test_ambiguous_second_rename_requires_new_readonly_check(self):
        cli = self.make("rename-reply-fail-second")
        m.stage(cli, self.new, self.v18, self.legacy)
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            m.promote(cli, self.new, self.v18, self.legacy)
        self.assertEqual(cli.rename_count, 2)
        self.assertEqual(cli.fs[m.ACTIVE], self.new)
        self.assertEqual(cli.fs[m.CURRENT_BACKUP], self.v18)
        self.assertEqual(cli.fs[m.LEGACY_BACKUP], self.legacy)
        # The command reply was unknown, so the simulated runner MUST stop,
        # even if a separate memory inspection reveals the rename occurred.

    def test_second_rename_not_allowlisted_before_first(self):
        cli = self.make()
        m.stage(cli, self.new, self.v18, self.legacy)
        with self.assertRaisesRegex(ValueError, "source/target"):
            m.rename_once(cli, m.NEW, m.ACTIVE)
        self.assertEqual(cli.rename_count, 0)

    def test_stat_only_allowed_fixed_paths(self):
        cli = self.make()
        with self.assertRaisesRegex(ValueError, "allowlisted"):
            m.stat(cli, "/ext/apps_data/labmate/profiles/s1.cfg")
        self.assertEqual(cli.commands, [])

    def test_mock_native_disallows_write_to_active_path(self):
        cli = self.make()
        with self.assertRaisesRegex(ValueError, "unapproved write path"):
            cli.send_and_wait_eol(f'storage write_chunk "{m.ACTIVE}" 16\r')
        self.assertEqual(cli.fs[m.ACTIVE], self.v18)

    def test_mock_native_disallows_rename_to_legacy_backup(self):
        cli = self.make()
        with self.assertRaisesRegex(ValueError, "unapproved rename"):
            cli.send_and_wait_eol(f'storage rename "{m.ACTIVE}" "{m.LEGACY_BACKUP}"\r')
        self.assertEqual(cli.fs[m.LEGACY_BACKUP], self.legacy)

    def test_no_direct_device_and_no_filesystem_apis(self):
        file = Path(m.__file__).read_text("utf-8")
        self.assertNotIn("import serial", file)
        self.assertNotIn("FlipperStorage", file)
        self.assertNotIn("storage remove", file)
        self.assertNotIn("storage mkdir", file)
        self.assertNotIn("storage format", file)
        self.assertNotIn("storage rm", file)

    def test_all_mock_operations_use_protected_paths(self):
        cli = self.make()
        m.stage(cli, self.new, self.v18, self.legacy)
        m.promote(cli, self.new, self.v18, self.legacy)
        self.assertTrue(all(
            cmd.startswith(("storage stat ", "storage write_chunk ", "storage rename "))
            for cmd in cli.commands
        ))


if __name__ == "__main__":
    unittest.main()
