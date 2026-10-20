#!/usr/bin/env python3
"""Offline-only actual independent postactivation checker test matrix."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_v19_e11_postactivation_ro as ro
import simulate_v19_e11_storage_cli_offline as fake


class PostactivationReadOnlyTest(unittest.TestCase):
    def setUp(self):
        self.v19 = b"LATEST_SAFE_STAGE" * 10
        self.v18 = b"LAST_STABLE_FINAL" * 10
        self.legacy = b"OLDER_E11_APP" * 9
        sha = lambda b: hashlib.sha256(b).hexdigest()
        for m in (ro, fake):
            for stem, data in (("V19", self.v19), ("V18", self.v18),
                               ("LEGACY", self.legacy)):
                if hasattr(m, stem+"_SIZE"):
                    x = patch.object(m, stem+"_SIZE", len(data))
                    x.start()
                    self.addCleanup(x.stop)
                if hasattr(m, stem+"_SHA"):
                    x = patch.object(m, stem+"_SHA", sha(data))
                    x.start()
                    self.addCleanup(x.stop)
        # The strict stat allowlist is bound at import-time to real FAP sizes.
        # Match it to synthetic fixture sizes ONLY in this offline test.
        sizes = patch.object(ro, "ALLOWED_SIZES",
                             frozenset((len(self.v19), len(self.v18), len(self.legacy))))
        sizes.start()
        self.addCleanup(sizes.stop)
        idpatch = patch.object(ro, "identity")
        idpatch.start()
        self.addCleanup(idpatch.stop)

    def device(self, activated=True, faults=()):
        d = fake.FakeCLI(self.v18, self.legacy, set(faults))
        if activated:
            d.fs[ro.ACTIVE] = self.v19
            d.fs[ro.CURRENT_BACKUP] = self.v18
        else:
            d.fs[ro.NEW] = self.v19
        return d

    def verify(self, cli, new=None, old=None, legacy=None):
        return ro.classify(cli, new if new is not None else self.v19,
                           old if old is not None else self.v18,
                           legacy if legacy is not None else self.legacy,
                           {}, {})

    def test_two_full_readbacks_of_both_v19_and_v18_and_historic_backup(self):
        d = self.device()
        with patch.object(d, "read_file", wraps=d.read_file) as reads:
            out = self.verify(d)
        self.assertEqual(reads.call_count, 6)
        self.assertEqual(out["v19_active"], "CONFIRMED_BY_TWO_FULL_SHA256_READBACKS")
        self.assertEqual(out["device_writes"], "ZERO")
        self.assertEqual(out["installed_firmware_binary_abi"], "NOT_ATTESTED")
        self.assertEqual(d.rename_count, 0)
        self.assertEqual(d.chunk_count, 0)
        self.assertTrue(all(cmd.startswith("storage stat ") for cmd in d.commands))

    def test_staged_v18_state_is_not_claimed_as_activated(self):
        d = self.device(activated=False)
        with self.assertRaises(ValueError):
            self.verify(d)
        self.assertEqual(d.rename_count, 0)

    def test_gap_after_first_rename_is_not_accepted(self):
        d = self.device(activated=False)
        d.fs[ro.CURRENT_BACKUP] = d.fs.pop(ro.ACTIVE)
        with self.assertRaises(ValueError):
            self.verify(d)

    def test_unexpected_stage_occupied_after_activation_fails_closed(self):
        d = self.device()
        d.fs[ro.NEW] = self.v19
        with self.assertRaisesRegex(ValueError, "forbidden sidecar"):
            self.verify(d)

    def test_failed_v19_retention_path_occupied_fails_closed(self):
        d = self.device()
        d.fs[ro.FAILED_V19_BACKUP] = self.v19
        with self.assertRaisesRegex(ValueError, "forbidden sidecar"):
            self.verify(d)

    def test_v18_final_backup_missing(self):
        d = self.device()
        del d.fs[ro.CURRENT_BACKUP]
        with self.assertRaises(ValueError):
            self.verify(d)

    def test_v18_final_backup_content_mutated(self):
        d = self.device()
        d.fs[ro.CURRENT_BACKUP] = b"X" + self.v18[1:]
        with self.assertRaisesRegex(ValueError, "MD5"):
            self.verify(d)

    def test_active_fap_byte_mutated(self):
        d = self.device()
        d.fs[ro.ACTIVE] = b"X" + self.v19[1:]
        with self.assertRaisesRegex(ValueError, "MD5"):
            self.verify(d)

    def test_historical_e11_backup_changed(self):
        d = self.device()
        d.fs[ro.LEGACY_BACKUP] = b"X" + self.legacy[1:]
        with self.assertRaisesRegex(ValueError, "MD5"):
            self.verify(d)

    def test_remote_command_echo_drift_fails_closed(self):
        d = self.device(faults=("echo-fail",))
        with self.assertRaises(ValueError):
            self.verify(d)
        self.assertEqual(d.rename_count, 0)

    def test_wrong_local_pinned_fap_fails_before_any_com_command(self):
        d = self.device()
        with self.assertRaisesRegex(ValueError, "invalid pinned PC"):
            self.verify(d, new=self.v19[:-1])
        self.assertEqual(d.commands, [])

    def test_unapproved_path_never_stat_queried(self):
        d = self.device()
        with self.assertRaisesRegex(ValueError, "unexpected post-activation stat path"):
            ro.stat(d, "/ext/apps_data/labmate/profiles/s1")
        self.assertEqual(d.commands, [])

    def test_corrupted_remote_full_readback_not_accepted(self):
        d = self.device()
        with patch.object(d, "read_file", wraps=lambda p:
                          b"?"*len(d.fs[p]) if p == ro.ACTIVE else d.fs[p]):
            with self.assertRaisesRegex(ValueError, "complete on-device binary"):
                self.verify(d)

    def test_identity_label_or_resources_failure_blocks(self):
        d = self.device()
        with patch.object(ro, "identity", side_effect=ValueError("native mismatch")):
            with self.assertRaisesRegex(ValueError, "native mismatch"):
                self.verify(d)
        self.assertEqual(d.rename_count, 0)

    def test_checker_contains_no_mutation_commands(self):
        source = Path(ro.__file__).read_text("utf-8")
        for word in ("storage rename ", "storage write_chunk ", "storage remove ",
                     "storage mkdir ", "storage format ", "FlipperStorageOperations("):
            self.assertNotIn(word, source)


if __name__ == "__main__":
    unittest.main()
