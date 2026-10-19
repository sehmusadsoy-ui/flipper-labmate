#!/usr/bin/env python3
"""Synthetic poststage read-only verification, never opens COM or writes FAP."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import simulate_v19_e11_storage_cli_offline as mockcli
import check_v19_e11_staged_device_ro as ro


class PoststageReadOnlyTest(unittest.TestCase):
    def setUp(self):
        self.v18 = b"V18_PREVIOUS_FINAL" * 6
        self.legacy = b"E11_V18_DEV" * 4
        self.fap = b"REAL_V19_STAGE_MODEL" * 900
        sha = lambda b: hashlib.sha256(b).hexdigest()
        self.patches = (
            (mockcli, "V18_SIZE", len(self.v18)),
            (mockcli, "V18_SHA", sha(self.v18)),
            (mockcli, "LEGACY_SIZE", len(self.legacy)),
            (mockcli, "LEGACY_SHA", sha(self.legacy)),
            (ro, "FAP_BYTES", len(self.fap)),
            (ro, "FAP_SHA", sha(self.fap)),
            (ro, "REMOTE_SIZE", f"File, size: {len(self.fap)}b".encode("ascii")),
        )
        for obj, name, value in self.patches:
            p = patch.object(obj, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.good = {
            "state": "AFTER_PROMOTION",
            "new_v18_FAP": "ACTIVE_MD5_AND_SIZE_PASS",
            "old_E11_FAP_preserved": "PC_BACKUP_AND_DEVICE_BAK",
            "firmware_JS_gpio_eventloop_manifest": "PINNED_MD5_AND_LABEL_MATCH",
        }
        self.audit = patch.object(ro, "audit", return_value=self.good)
        self.audit.start()
        self.addCleanup(self.audit.stop)

    def device(self, *, staged=True, faults=()):
        d = mockcli.FakeCLI(self.v18, self.legacy, set(faults))
        if staged:
            d.fs[ro.STAGE] = self.fap
        return d

    def attest(self, device):
        return ro.attest_poststage(device, {"E11_APP":"pinned"}, {},
                                   hashlib.md5(self.v18).hexdigest(), self.fap)

    def test_two_full_readbacks_success_without_any_device_write(self):
        d = self.device()
        with patch.object(d, "read_file", wraps=d.read_file) as readback:
            result = self.attest(d)
        self.assertEqual(readback.call_count, 2)
        self.assertEqual(result["v19_active"], "NO")
        self.assertEqual(result["device_writes"], "ZERO")
        self.assertEqual(result["future_recovery_filename"], "ABSENT")
        self.assertEqual(d.fs[ro.STAGE], self.fap)
        self.assertEqual(d.fs[mockcli.ACTIVE], self.v18)
        self.assertEqual(d.fs[mockcli.LEGACY_BACKUP], self.legacy)
        self.assertEqual(d.rename_count, 0)
        self.assertEqual(d.chunk_count, 0)
        self.assertTrue(all(command.startswith("storage stat ") for command in d.commands))

    def test_stage_missing_blocks_attestation(self):
        d = self.device(staged=False)
        with self.assertRaisesRegex(ValueError, "not exactly present"):
            self.attest(d)

    def test_stage_size_wrong_blocks_attestation(self):
        d = self.device()
        d.fs[ro.STAGE] = self.fap[:-1]
        # Strict stat parser rejects any unpinned size BEFORE content read.
        with self.assertRaisesRegex(ValueError, "unrecognized post-stage status response"):
            self.attest(d)
        self.assertEqual(d.chunk_count, 0)
        self.assertEqual(d.rename_count, 0)

    def test_stage_same_size_mutation_blocks_md5(self):
        d = self.device()
        d.fs[ro.STAGE] = b"!" + self.fap[1:]
        with self.assertRaisesRegex(ValueError, "MD5 mismatch"):
            self.attest(d)

    def test_remote_stage_md5_fault_blocks_attestation(self):
        d = self.device(faults=("stage-md5-bad",))
        with self.assertRaisesRegex(ValueError, "MD5 mismatch"):
            self.attest(d)

    def test_corrupt_full_binary_readback_blocks_attestation(self):
        d = self.device(faults=("stage-readback-corrupt",))
        with self.assertRaisesRegex(ValueError, "full staged file SHA256"):
            self.attest(d)

    def test_no_future_backup_allowed(self):
        d = self.device()
        d.fs[ro.RECOVERY] = self.v18
        # Any unexpected-size reply fails CLOSED at exact stat parser.
        with self.assertRaisesRegex(ValueError, "unrecognized post-stage status response"):
            self.attest(d)
        self.assertEqual(d.chunk_count, 0)
        self.assertEqual(d.rename_count, 0)

    def test_reserved_recovery_filename_occupied_even_at_stage_size(self):
        d = self.device()
        d.fs[ro.RECOVERY] = self.fap
        # A recognized-size file still fails the explicit absent-only gate.
        with self.assertRaisesRegex(ValueError, "unexpectedly occupied"):
            self.attest(d)
        self.assertEqual(d.chunk_count, 0)
        self.assertEqual(d.rename_count, 0)

    def test_installed_active_v18_identity_drift_blocks_attestation(self):
        d = self.device()
        self.audit.stop()
        with patch.object(ro, "audit", return_value={
            **self.good, "new_v18_FAP": "CORRUPT"
        }):
            with self.assertRaisesRegex(ValueError, "resource drift"):
                self.attest(d)

    def test_native_resource_identity_drift_blocks_attestation(self):
        d = self.device()
        self.audit.stop()
        with patch.object(ro, "audit", return_value={
            **self.good, "firmware_JS_gpio_eventloop_manifest": "DRIFT"
        }):
            with self.assertRaisesRegex(ValueError, "resource drift"):
                self.attest(d)

    def test_native_drift_between_readbacks_blocks_attestation(self):
        d = self.device()
        self.audit.stop()
        with patch.object(ro, "audit", side_effect=[
            dict(self.good), dict(self.good), dict(self.good, marker="CHANGED")
        ]):
            with self.assertRaisesRegex(ValueError, "identity changed"):
                self.attest(d)

    def test_wrong_local_candidate_before_any_remote_action(self):
        d = self.device()
        with self.assertRaisesRegex(ValueError, "incorrect local"):
            ro.attest_poststage(d, {"E11_APP":"ok"}, {},
                                hashlib.md5(self.v18).hexdigest(), self.fap[:-1])
        self.assertEqual(d.commands, [])

    def test_unapproved_remote_stat_path_rejected(self):
        d = self.device()
        with self.assertRaisesRegex(ValueError, "forbidden"):
            ro.stat_exact(d, "/ext/apps_data/labmate/profiles/s1")
        self.assertEqual(d.commands, [])

    def test_bad_native_cli_command_echo_rejected(self):
        d = self.device(faults=("echo-fail",))
        with self.assertRaises(ValueError):
            self.attest(d)

    def test_checker_source_contains_no_device_mutation_commands(self):
        source = Path(ro.__file__).read_text("utf-8")
        for cmd in ('storage write_chunk ', 'storage rename ', 'storage remove ',
                    'storage rm ', 'storage format ', 'storage mkdir '):
            self.assertNotIn(cmd, source)
        self.assertNotIn("stage_v19_e11_sidecar_only", source)
        self.assertNotIn("serial.Serial(", source)

    def test_report_never_claims_live_abi_proven_or_activation(self):
        d = self.device()
        result = self.attest(d)
        self.assertIn("NOT_FIRMWARE_ABI_ATTESTATION", result["firmware_js_manifest_label"])
        self.assertEqual(result["activation_authorized"], "NO")


if __name__ == "__main__":
    unittest.main()
