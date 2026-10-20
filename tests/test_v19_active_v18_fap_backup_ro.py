#!/usr/bin/env python3
"""Offline negative regressions for v1.9 read-only LIVE v1.8 FAP backup gate.

No USB/Flipper, no user paths, no firmware writes. Mock on-device readback.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import backup_v19_active_v18_fap_ro as m


class FakeClient:
    def __init__(self, data):
        self.data = data
        self.paths = []

    def read_file(self, path):
        self.paths.append(path)
        return self.data


class ReadOnlyBackupTest(unittest.TestCase):
    def setUp(self):
        self.data = b"example synthetic FAP for offline unit tests"
        self.digest = hashlib.sha256(self.data).hexdigest()
        self.good = {
            "state": "AFTER_PROMOTION",
            "new_v18_FAP": "ACTIVE_MD5_AND_SIZE_PASS",
        }
        self.post = {"E11_APP": "unused-in-mock"}
        self.patches = [
            patch.object(m, "EXPECTED_ACTIVE_BYTES", len(self.data)),
            patch.object(m, "EXPECTED_ACTIVE_SHA", self.digest),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_verified_binary_read_success_and_double_screen(self):
        client = FakeClient(bytearray(self.data))
        with patch.object(m, "audit", side_effect=[self.good, self.good]) as check:
            out = m.readback_exact(client, self.post, {}, hashlib.md5(self.data).hexdigest())
        self.assertEqual(out, self.data)
        self.assertEqual(client.paths, ["/ext/apps/Tools/labmate.fap"])
        self.assertEqual(check.call_count, 2)

    def test_refuse_unexpected_state_before_read(self):
        client = FakeClient(self.data)
        with patch.object(m, "audit", return_value={"state": "BEFORE_PROMOTION"}):
            with self.assertRaises(ValueError):
                m.readback_exact(client, self.post, {}, hashlib.md5(self.data).hexdigest())
        self.assertEqual(client.paths, [])

    def test_refuse_binary_mismatch(self):
        wrong = b"X" * len(self.data)
        client = FakeClient(wrong)
        with patch.object(m, "audit", return_value=self.good) as check:
            with self.assertRaises(ValueError):
                m.readback_exact(client, self.post, {}, hashlib.md5(self.data).hexdigest())
        self.assertEqual(check.call_count, 1)

    def test_refuse_nontyped_readback(self):
        client = FakeClient("not bytes")
        with patch.object(m, "audit", return_value=self.good):
            with self.assertRaises(ValueError):
                m.readback_exact(client, self.post, {}, hashlib.md5(self.data).hexdigest())

    def test_refuse_postread_device_identity_drift(self):
        client = FakeClient(self.data)
        changed = dict(self.good, firmware_JS_gpio_eventloop_manifest="CHANGED")
        with patch.object(m, "audit", side_effect=[self.good, changed]):
            with self.assertRaises(ValueError):
                m.readback_exact(client, self.post, {}, hashlib.md5(self.data).hexdigest())

    def test_backup_exact_new_pc_folder_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "new-folder"
            saved = m.write_backup(target, self.data)
            self.assertEqual(saved.read_bytes(), self.data)
            self.assertTrue((target / m.MARKER).is_file())
            self.assertFalse((target / "INCOMPLETE_DO_NOT_RESTORE.txt").exists())
            with self.assertRaises(ValueError):
                m.write_backup(target, self.data)

    def test_refuse_corrupt_payload_before_creating_pc_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "new-folder"
            with self.assertRaises(ValueError):
                m.write_backup(target, b"bad")
            self.assertFalse(target.exists())

    def test_refuse_relative_pc_folder(self):
        with self.assertRaises(ValueError):
            m.check_destination(Path("relative/backup"))


if __name__ == "__main__":
    unittest.main()
