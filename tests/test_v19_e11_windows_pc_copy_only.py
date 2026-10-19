#!/usr/bin/env python3
"""Host-only tests for WSL->Windows v1.9 candidate PC copy; zero serial calls."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import copy_v19_e11_candidate_windows_pc_only as m


class PCOnlyWindowsCopyTest(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name)
        self.candidate = self.root / "v19.fap"
        self.blob = b"V19-LOCAL-FAP-SYNTHETIC" * 17
        self.candidate.write_bytes(self.blob)
        self.patch_values = []
        for name, value in (
            ("FAP_BYTES", len(self.blob)),
            ("FAP_SHA", hashlib.sha256(self.blob).hexdigest())
        ):
            p = patch.object(m, name, value)
            p.start()
            self.addCleanup(p.stop)

    def test_matching_candidate_exact_bytes_verified(self):
        self.assertEqual(m.source_candidate(self.candidate), self.blob)

    def test_modified_fap_hash_refused(self):
        self.candidate.write_bytes(b"?" + self.blob[1:])
        with self.assertRaisesRegex(ValueError, "SHA256"):
            m.source_candidate(self.candidate)

    def test_missing_fap_refused(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            m.source_candidate(self.root / "nothing.fap")

    def test_symlink_source_refused(self):
        link = self.root / "link.fap"
        link.symlink_to(self.candidate)
        with self.assertRaisesRegex(ValueError, "missing/unsafe"):
            m.source_candidate(link)

    def test_destination_exists_refused(self):
        folder = self.root / "V19-WINDOWS-PC-CANDIDATE-one"
        folder.mkdir()
        with self.assertRaisesRegex(ValueError, "not safe or not fresh"):
            m.destination_check(self.root, folder, (self.candidate,))

    def test_wrong_windows_root_refused(self):
        folder = self.root / "V19-WINDOWS-PC-CANDIDATE-two"
        with self.assertRaisesRegex(ValueError, "allow only"):
            m.destination_check(self.root, folder, (self.candidate,))

    def test_pc_only_copy_exact_inventory_and_sha_after_fsync(self):
        output = self.root / "fresh-pc-copy"
        live = self.root / "backup-v18"
        prior = self.root / "backup-e11"
        snapshot = self.root / "data"
        for p in (live, prior, snapshot):
            p.mkdir()
        def mock_destination(root, dest, sources):
            if root != self.root or dest.exists() or dest.parent != self.root:
                raise ValueError("unsafe mock destination")
            if any(dest == source for source in sources):
                raise ValueError("overlap")
        with patch.object(m, "verify_backups", return_value=(12, 2128)), patch.object(
                m, "destination_check", side_effect=mock_destination):
            report = m.copy_pc_only(
                self.candidate, self.root, output, live, prior, snapshot)
        self.assertEqual(report["device_writes"], "NONE")
        self.assertEqual(report["install_authorized"], "NO")
        self.assertEqual((output / m.PC_FILENAME).read_bytes(), self.blob)
        self.assertTrue((output / m.MARKER).is_file())
        self.assertTrue((output / m.MANIFEST).is_file())
        self.assertFalse((output / m.INCOMPLETE).exists())
        self.assertEqual(len(list(output.iterdir())), 3)

    def test_existing_pc_folder_never_overwritten_on_retry(self):
        output = self.root / "PC-Copy"
        output.mkdir()
        keep = output / "important.csv"
        keep.write_text("keep me unchanged", encoding="utf-8")
        backup = self.root / "backup"
        backup.mkdir()
        with patch.object(m, "verify_backups", return_value=(12, 2128)):
            with self.assertRaises(ValueError):
                m.copy_pc_only(self.candidate, self.root, output, backup, backup, backup)
        self.assertEqual(keep.read_text("utf-8"), "keep me unchanged")

    def test_module_never_imports_serial_transport(self):
        data = Path(m.__file__).read_text("utf-8")
        self.assertNotIn("import serial", data)
        self.assertNotIn("FlipperStorage", data)
        self.assertNotIn("storage write_chunk", data)
        self.assertNotIn("storage rename ", data)
        self.assertNotIn("storage remove ", data)


if __name__ == "__main__":
    unittest.main()
