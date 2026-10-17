#!/usr/bin/env python3
"""Synthetic-only E11 backup gate tests. No Flipper, private files, or firmware."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_v18_e11_pc_backup_gate import verify, MANIFEST, VERIFIED, INCOMPLETE


class BackupGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.old = root / "historical"
        self.current = root / "current"
        self.old.mkdir()
        self.current.mkdir()
        for i in range(14):
            (self.old / ("history_%02d.csv" % i)).write_bytes(b"old-" + bytes([i]))
        payloads = {("log_%04d.csv" % i): bytes([i + 33]) * (180 if i < 9 else 171)
                    for i in range(10)}
        self.files = {}
        for name, data in payloads.items():
            (self.current / name).write_bytes(data)
            self.files[name] = {
                "size_bytes": len(data),
                "md5_device_screen": hashlib.md5(data).hexdigest(),
                "sha256_of_pc_readback": hashlib.sha256(data).hexdigest(),
            }
        (self.current / VERIFIED).write_text("PC only verified, not restore\n")
        self.write_manifest()

    def write_manifest(self, **updates):
        report = {
            "snapshot_scope": "ONLY /ext/apps_data/labmate",
            "snapshot_complete": True, "device_write": False,
            "historical_backup_modified": False, "full_microSD_backup": False,
            "restoration_rehearsed": False, "install_authorized": False,
            "files": self.files,
        }
        report.update(updates)
        (self.current / MANIFEST).write_text(json.dumps(report), encoding="utf-8")

    def test_good_two_state_snapshots(self):
        self.assertEqual(verify(self.old, self.current),
                         {"historical_files": 14, "current_files": 10,
                          "current_bytes": 1791})

    def test_tampered_current_file_rejected(self):
        (self.current / "log_0000.csv").write_bytes(b"x" * 180)
        with self.assertRaisesRegex(ValueError, "checksum"):
            verify(self.old, self.current)

    def test_missing_current_file_rejected(self):
        (self.current / "log_0000.csv").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            verify(self.old, self.current)

    def test_incomplete_marker_rejected(self):
        (self.current / INCOMPLETE).write_text("bad")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            verify(self.old, self.current)

    def test_historical_count_rejected(self):
        (self.old / "history_00.csv").unlink()
        with self.assertRaisesRegex(ValueError, "14-file"):
            verify(self.old, self.current)

    def test_forged_or_changed_total_rejected(self):
        data = (self.current / "log_0009.csv").read_bytes() + b"x"
        (self.current / "log_0009.csv").write_bytes(data)
        self.files["log_0009.csv"] = {
            "size_bytes": len(data),
            "md5_device_screen": hashlib.md5(data).hexdigest(),
            "sha256_of_pc_readback": hashlib.sha256(data).hexdigest(),
        }
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "1791-byte"):
            verify(self.old, self.current)

    def test_scope_or_install_consent_forgery_rejected(self):
        self.write_manifest(install_authorized=True)
        with self.assertRaisesRegex(ValueError, "provenance"):
            verify(self.old, self.current)

    def test_traversal_key_rejected(self):
        self.files["../evil.csv"] = self.files.pop("log_0000.csv")
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "unsafe snapshot"):
            verify(self.old, self.current)

    def test_added_untracked_file_rejected(self):
        (self.current / "other.bin").write_bytes(b"x")
        with self.assertRaisesRegex(ValueError, "unlisted extra"):
            verify(self.old, self.current)

    def test_alias_or_symlink_rejected(self):
        alias = self.current / "badalias"
        try:
            alias.symlink_to(self.current / "log_0000.csv")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable in current OS")
        with self.assertRaisesRegex(ValueError, "symlink"):
            verify(self.old, self.current)

    def test_no_overlapping_backup_directories(self):
        with self.assertRaisesRegex(ValueError, "overlap"):
            verify(self.old, self.old)


if __name__ == "__main__":
    unittest.main()
