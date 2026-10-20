#!/usr/bin/env python3
"""Unit tests of actual stage-only orchestration via zero-device FakeCLI.

This tests replay script and catches its mock boundary regressions before
feeding it the hash-pinned 97,540-byte *real* user PC-built FAP.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import replay_v19_e11_real_fap_stage_offline as r


class ReplayActualStageCodeMockTest(unittest.TestCase):
    def setUp(self):
        self.v18 = b"full old v18" * 8
        self.legacy = b"earlier E11 dev" * 4
        self.new = b"v19 actual stage code path" * 100
        sh = lambda x: hashlib.sha256(x).hexdigest()
        values = {
            (r, "V19_SIZE"): len(self.new), (r, "V19_SHA"): sh(self.new),
            (r, "V18_SIZE"): len(self.v18), (r, "V18_SHA"): sh(self.v18),
            (r, "LEGACY_SIZE"): len(self.legacy), (r, "LEGACY_SHA"): sh(self.legacy),
            (r.fixture, "V19_SIZE"): len(self.new),
            (r.fixture, "V19_SHA"): sh(self.new),
            (r.fixture, "V18_SIZE"): len(self.v18),
            (r.fixture, "V18_SHA"): sh(self.v18),
            (r.fixture, "LEGACY_SIZE"): len(self.legacy),
            (r.fixture, "LEGACY_SHA"): sh(self.legacy),
            (r.stage, "FAP_BYTES"): len(self.new),
            (r.stage, "FAP_SHA"): sh(self.new),
            (r.stage, "V18_ACTIVE_BYTES"): len(self.v18),
        }
        for (module, name), value in values.items():
            p = patch.object(module, name, value)
            p.start()
            self.addCleanup(p.stop)

    def test_complete_direct_stage_code_replay_preserves_active_v18(self):
        fake, output = r.replay(self.new, self.v18, self.legacy)
        self.assertEqual(fake.fs[r.stage.APP], self.v18)
        self.assertEqual(fake.fs[r.stage.STAGE], self.new)
        self.assertEqual(fake.fs[r.stage.LEGACY], self.legacy)
        self.assertEqual(fake.rename_count, 0)
        self.assertEqual(output["stage_only"], "PASS_FULL_DEVICE_BINARY_READBACK")
        self.assertFalse(any(x.startswith("storage rename ") for x in fake.commands))

    def test_wrong_candidate_sha_blocks_replay(self):
        with self.assertRaisesRegex(ValueError, "unverified PC input"):
            r.replay(b"?" + self.new[1:], self.v18, self.legacy)

    def test_wrong_candidate_length_blocks_replay(self):
        with self.assertRaisesRegex(ValueError, "unverified PC input"):
            r.replay(self.new[:-1], self.v18, self.legacy)

    def test_wrong_active_v18_blocks_replay(self):
        with self.assertRaisesRegex(ValueError, "unverified PC input"):
            r.replay(self.new, b"!" + self.v18[1:], self.legacy)

    def test_wrong_old_e11_backup_blocks_replay(self):
        with self.assertRaisesRegex(ValueError, "unverified PC input"):
            r.replay(self.new, self.v18, b"!" + self.legacy[1:])

    def test_reject_bad_native_ready(self):
        with self.assertRaisesRegex(ValueError, "Ready mismatch"):
            r.replay(self.new, self.v18, self.legacy, faults=frozenset(("bad-ready",)))

    def test_reject_bad_native_echo(self):
        with self.assertRaises(ValueError):
            r.replay(self.new, self.v18, self.legacy, faults=frozenset(("echo-fail",)))

    def test_short_write_stops_without_rename(self):
        with self.assertRaisesRegex(ValueError, "short serial write"):
            r.replay(self.new, self.v18, self.legacy,
                     faults=frozenset(("short-first-chunk",)))

    def test_ambiguous_native_write_response_stops(self):
        with self.assertRaisesRegex(ValueError, "ambiguous native CLI write"):
            r.replay(self.new, self.v18, self.legacy,
                     faults=frozenset(("chunk-tail-fail",)))

    def test_stage_md5_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "MD5 mismatch"):
            r.replay(self.new, self.v18, self.legacy,
                     faults=frozenset(("stage-md5-bad",)))

    def test_stage_full_binary_readback_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "SHA256 readback mismatch"):
            r.replay(self.new, self.v18, self.legacy,
                     faults=frozenset(("stage-readback-corrupt",)))

    def test_unknown_fault_scope_rejected(self):
        with self.assertRaisesRegex(ValueError, "unapproved virtual fault"):
            r.replay(self.new, self.v18, self.legacy,
                     faults=frozenset(("unknown-device-operation",)))


if __name__ == "__main__":
    unittest.main()
