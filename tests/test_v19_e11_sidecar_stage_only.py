#!/usr/bin/env python3
"""Synthetic-only v1.9 review stage tests; ZERO actual USB/COM.

All 'device' calls go to the in-memory FakeCLI. An expressly authorized
real-device stage is a separate later decision; running these tests never
writes to the Flipper, copies an FAP, or touches PC user backups.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import simulate_v19_e11_storage_cli_offline as fake
import stage_v19_e11_sidecar_only as m


class StageOnlyMockTest(unittest.TestCase):
    def setUp(self):
        self.v18 = b"FINAL V18" * 6
        self.legacy = b"E11 V18DEV OLD" * 4
        self.fap = b"V19-E11-LOGIC-SCOPE-REAL-SIZED-FAP-MOCK" * 3750
        self.digest = hashlib.sha256(self.fap).hexdigest()
        self.patches = {
            (fake, "V18_SIZE"): len(self.v18),
            (fake, "V18_SHA"): hashlib.sha256(self.v18).hexdigest(),
            (fake, "LEGACY_SIZE"): len(self.legacy),
            (fake, "LEGACY_SHA"): hashlib.sha256(self.legacy).hexdigest(),
            (fake, "V19_SIZE"): len(self.fap),
            (fake, "V19_SHA"): self.digest,
            (m, "FAP_BYTES"): len(self.fap),
            (m, "FAP_SHA"): self.digest,
        }
        for (module, name), value in self.patches.items():
            p = patch.object(module, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.post = {"E11_APP": "original-pinned-resources"}
        self.js = {}
        self.old_md5 = hashlib.md5(self.v18).hexdigest()
        self.good_report = {
            "state": "AFTER_PROMOTION",
            "new_v18_FAP": "ACTIVE_MD5_AND_SIZE_PASS",
            "old_E11_FAP_preserved": "PC_BACKUP_AND_DEVICE_BAK",
            "firmware_JS_gpio_eventloop_manifest": "PINNED_MD5_AND_LABEL_MATCH",
        }
        self.preaudit = patch.object(
            m, "attest_current_v18_and_free_names",
            return_value={"v19_reserved_paths": "BOTH_ABSENT_TWICE"},
        )
        self.audit = patch.object(m, "audit", return_value=self.good_report)
        self.preaudit.start()
        self.audit.start()
        self.addCleanup(self.preaudit.stop)
        self.addCleanup(self.audit.stop)

    def client(self, *faults):
        return fake.FakeCLI(self.v18, self.legacy, set(faults))

    def run_stage(self, client):
        return m.stage_only(client, self.fap, self.post, self.js, self.old_md5)

    def test_stage_only_keeps_v18_active_and_e11_backup(self):
        client = self.client()
        report = self.run_stage(client)
        self.assertEqual(report["stage_only"], "PASS_FULL_DEVICE_BINARY_READBACK")
        self.assertEqual(report["v19_active"], "NO")
        self.assertEqual(report["rename_performed"], "NO")
        self.assertEqual(client.fs[m.APP], self.v18)
        self.assertEqual(client.fs[m.LEGACY], self.legacy)
        self.assertEqual(client.fs[m.STAGE], self.fap)
        self.assertNotIn(m.BACKUP, client.fs)
        self.assertEqual(client.rename_count, 0)
        self.assertEqual(
            client.chunk_count, (len(self.fap) + m.BUF - 1) // m.BUF
        )
        self.assertFalse(any("storage rename " in name for name in client.commands))

    def test_candidate_rejected_before_any_device_command(self):
        client = self.client()
        with self.assertRaisesRegex(ValueError, "wrong v1.9"):
            m.stage_only(client, self.fap[:-1], self.post, self.js, self.old_md5)
        self.assertEqual(client.commands, [])

    def test_reject_double_stage_no_retry(self):
        client = self.client()
        self.run_stage(client)
        original_count = client.chunk_count
        with self.assertRaisesRegex(ValueError, "already exists|ambiguous"):
            self.run_stage(client)
        self.assertEqual(client.chunk_count, original_count)
        self.assertEqual(client.fs[m.APP], self.v18)

    def test_reject_partial_existing_stage(self):
        client = self.client()
        client.fs[m.STAGE] = b"partial"
        with self.assertRaises(ValueError):
            self.run_stage(client)
        self.assertEqual(client.chunk_count, 0)

    def test_reject_backup_target_occupied(self):
        client = self.client()
        client.fs[m.BACKUP] = b"occupied"
        with self.assertRaises(ValueError):
            self.run_stage(client)
        self.assertEqual(client.chunk_count, 0)

    def test_reject_bad_ready_and_leave_v18(self):
        client = self.client("bad-ready")
        with self.assertRaisesRegex(ValueError, "Ready mismatch"):
            self.run_stage(client)
        self.assertEqual(client.fs[m.APP], self.v18)
        self.assertNotIn(m.STAGE, client.fs)
        self.assertEqual(client.chunk_count, 0)

    def test_reject_echo_drift_and_leave_v18(self):
        client = self.client("echo-fail")
        with self.assertRaises(ValueError):
            self.run_stage(client)
        self.assertEqual(client.fs[m.APP], self.v18)
        self.assertEqual(client.chunk_count, 0)

    def test_short_first_chunk_leaves_partial_nonapp_stage(self):
        client = self.client("short-first-chunk")
        with self.assertRaisesRegex(ValueError, "short serial write"):
            self.run_stage(client)
        self.assertEqual(client.fs[m.APP], self.v18)
        self.assertIn(m.STAGE, client.fs)
        self.assertLess(len(client.fs[m.STAGE]), len(self.fap))
        self.assertEqual(client.rename_count, 0)

    def test_error_tail_rejected_before_second_chunk(self):
        client = self.client("chunk-tail-fail")
        with self.assertRaisesRegex(ValueError, "ambiguous native CLI write"):
            self.run_stage(client)
        self.assertEqual(client.fs[m.APP], self.v18)
        self.assertEqual(client.chunk_count, 1)

    def test_corrupted_device_stage_md5_blocks_pass(self):
        client = self.client("stage-md5-bad")
        with self.assertRaisesRegex(ValueError, "MD5 mismatch"):
            self.run_stage(client)
        self.assertEqual(client.fs[m.APP], self.v18)

    def test_corrupted_readback_blocks_pass(self):
        client = self.client("stage-readback-corrupt")
        with self.assertRaisesRegex(ValueError, "SHA256 readback mismatch"):
            self.run_stage(client)
        self.assertEqual(client.fs[m.APP], self.v18)

    def test_native_e11_resource_drift_blocks_pass(self):
        client = self.client()
        self.audit.stop()
        with patch.object(m, "audit", return_value=dict(
            self.good_report,
            firmware_JS_gpio_eventloop_manifest="BAD"
        )):
            with self.assertRaisesRegex(ValueError, "resources changed"):
                self.run_stage(client)
        self.assertEqual(client.fs[m.APP], self.v18)
        self.assertEqual(client.rename_count, 0)

    def test_active_app_state_drift_blocks_pass(self):
        client = self.client()
        self.audit.stop()
        with patch.object(m, "audit", return_value=dict(
            self.good_report, new_v18_FAP="BAD"
        )):
            with self.assertRaisesRegex(ValueError, "no longer unchanged"):
                self.run_stage(client)
        self.assertEqual(client.fs[m.APP], self.v18)

    def test_preflight_absence_mandatory(self):
        client = self.client()
        self.preaudit.stop()
        with patch.object(m, "attest_current_v18_and_free_names",
                          return_value={"v19_reserved_paths": "NO"}):
            with self.assertRaisesRegex(ValueError, "absent twice"):
                self.run_stage(client)
        self.assertEqual(client.chunk_count, 0)

    def test_exact_reserved_sidecar_is_only_write_target(self):
        client = self.client()
        self.run_stage(client)
        commands = [s for s in client.commands if s.startswith("storage write_chunk ")]
        self.assertGreater(len(commands), 0)
        self.assertTrue(all(f'"{m.STAGE}"' in x for x in commands))
        self.assertTrue(all(m.APP not in s for s in commands))
        self.assertTrue(all(m.BACKUP not in s for s in commands))

    def test_wrong_stat_path_rejected_without_calls(self):
        client = self.client()
        with self.assertRaises(ValueError):
            m.stat_exact(client, "/ext/apps_data/labmate/s1")
        self.assertEqual(client.commands, [])

    def test_wrong_md5_path_rejected(self):
        client = self.client()
        with self.assertRaises(ValueError):
            m.require_md5(client, m.LEGACY, "0" * 32)

    def test_reject_mismatched_pc_fap_size_or_hash(self):
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "review.fap"
            path.write_bytes(b"?" * len(self.fap))
            with self.assertRaisesRegex(ValueError, "content changed"):
                m.verified_candidate(path)
            path.write_bytes(self.fap[:-1])
            with self.assertRaisesRegex(ValueError, "missing/unsafe"):
                m.verified_candidate(path)

    def test_reject_unexpected_binary_write_chunk_size(self):
        client = self.client()
        with self.assertRaisesRegex(ValueError, "invalid binary"):
            m.send_stage_chunk(client, b"x" * (m.BUF + 1))
        self.assertEqual(client.commands, [])

    def test_no_app_promotion_or_device_reset_capability(self):
        source = Path(m.__file__).read_text("utf-8")
        self.assertNotIn("storage rename ", source)
        self.assertNotIn("storage remove ", source)
        self.assertNotIn("storage format ", source)
        self.assertNotIn("storage mkdir ", source)
        self.assertNotIn("storage rm ", source)
        self.assertNotIn("reset(", source)
        self.assertNotIn("flash(", source)

    def test_reject_wrong_auth_presentation_in_main_without_device(self):
        with patch.object(sys, "argv", [
            "stage_v19_e11_sidecar_only.py", "--port", "COM7",
            "--momentum-scripts", "/no", "--old-candidate", "/no",
            "--saved-old-fap-backup", "/no", "--final-v18-fap", "/no",
            "--active-v18-backup", "/no", "--data-snapshot", "/no",
            "--candidate", "/no", "--authorize-stage-only", "NO"
        ]):
            self.assertEqual(m.main(), 1)


if __name__ == "__main__":
    unittest.main()
