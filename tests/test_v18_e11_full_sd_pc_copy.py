#!/usr/bin/env python3
"""Synthetic filesystem backup tests; never mount/copy a real Flipper SD."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from backup_v18_e11_sd_reader_to_pc import copy_and_verify_sd, inventory


class SDReaderPCCopyTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.sd = self.root / "removable-source"
        (self.sd / "apps" / "Tools").mkdir(parents=True)
        (self.sd / "apps_data" / "labmate").mkdir(parents=True)
        (self.sd / "apps_data" / "Other App").mkdir(parents=True)
        (self.sd / "apps_data" / "café").mkdir(parents=True)
        (self.sd / "assets").mkdir()
        (self.sd / "System Config.dat").write_bytes(b"config")
        (self.sd / ".private-hidden.dat").write_bytes(b"secret")
        (self.sd / "apps" / "Tools" / "labmate.fap").write_bytes(b"one-FAP")
        (self.sd / "apps_data" / "labmate" / "log_0050.csv").write_bytes(b"rows")
        (self.sd / "apps_data" / "Other App" / "my...settings.ini").write_bytes(b"settings")
        (self.sd / "apps_data" / "café" / "notes.txt").write_bytes(b"unicode")
        self.out = self.root / "PC-new-full-copy"

    def test_preserves_nested_hidden_unicode_empty_directories(self):
        dirs, files = inventory(self.sd)
        self.assertIn("assets", dirs)
        self.assertIn(".private-hidden.dat", files)
        self.assertIn("apps_data/café/notes.txt", files)
        before = {n: hashlib.sha256((self.sd/n).read_bytes()).hexdigest() for n in files}
        result = copy_and_verify_sd(self.sd, self.out)
        self.assertEqual(result["files_copied_and_sha256_verified"], len(files))
        self.assertEqual(result["directories_recorded"], len(dirs))
        self.assertTrue((self.out / "assets").is_dir())
        self.assertEqual((self.out / "apps_data" / "café" / "notes.txt").read_bytes(), b"unicode")
        self.assertEqual((self.out / ".private-hidden.dat").read_bytes(), b"secret")
        self.assertFalse((self.out / "INCOMPLETE-DO-NOT-RESTORE.txt").exists())
        self.assertTrue((self.out / "READ_ONLY_PC_FILE_SNAPSHOT_VERIFIED.txt").exists())
        report = json.loads((self.out / "PC_ONLY_SD_SHA256_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertFalse(report["restore_rehearsed"])
        self.assertFalse(report["filesystem_metadata_or_raw_image_verified"])
        self.assertEqual(set(report["files"]), set(files))
        for name, digest in before.items():
            self.assertEqual(report["files"][name]["sha256"], digest)
            self.assertEqual(hashlib.sha256((self.sd/name).read_bytes()).hexdigest(), digest)
        self.assertEqual(result["source_sd_written"], "NO")
        self.assertEqual(result["firmware_flash_authorized"], "NO")

    def test_existing_pc_folder_refused_without_overwrite(self):
        self.out.mkdir()
        keep = self.out / "keep"
        keep.write_bytes(b"old")
        with self.assertRaisesRegex(ValueError, "already exists"):
            copy_and_verify_sd(self.sd, self.out)
        self.assertEqual(keep.read_bytes(), b"old")

    def test_source_overlap_refused(self):
        with self.assertRaisesRegex(ValueError, "overlap"):
            copy_and_verify_sd(self.sd, self.sd / "output")
        self.assertFalse((self.sd/"output").exists())

    def test_pc_parent_missing_refused(self):
        with self.assertRaisesRegex(ValueError, "parent"):
            copy_and_verify_sd(self.sd, self.root/"missing"/"backup")

    def test_linked_source_refused(self):
        linked = self.sd/"apps_data"/"Other App"/"linked.data"
        linked.symlink_to(self.sd/"System Config.dat")
        with self.assertRaisesRegex(ValueError, "link"):
            copy_and_verify_sd(self.sd, self.out)
        self.assertFalse(self.out.exists())

    def test_missing_flipper_root_refused(self):
        (self.sd/"apps_data"/"labmate"/"log_0050.csv").unlink()
        (self.sd/"apps_data"/"labmate").rmdir()
        with self.assertRaisesRegex(ValueError, "not a recognized"):
            copy_and_verify_sd(self.sd,self.out)
        self.assertFalse(self.out.exists())

    def test_reject_if_not_enough_pc_space(self):
        class Tiny:
            free = 1
        with patch("backup_v18_e11_sd_reader_to_pc.shutil.disk_usage", return_value=Tiny()):
            with self.assertRaisesRegex(ValueError, "insufficient"):
                copy_and_verify_sd(self.sd,self.out)
        self.assertFalse(self.out.exists())

    def test_changed_source_content_never_yields_complete_marker(self):
        from backup_v18_e11_sd_reader_to_pc import _sha
        original = _sha
        def altered(path):
            if self.out.exists() and str(path).startswith(str(self.sd)):
                return "0"*64
            return original(path)
        with patch("backup_v18_e11_sd_reader_to_pc._sha",side_effect=altered):
            with self.assertRaisesRegex(ValueError, "SD content changed"):
                copy_and_verify_sd(self.sd,self.out)
        self.assertTrue((self.out/"INCOMPLETE-DO-NOT-RESTORE.txt").exists())
        self.assertFalse((self.out/"READ_ONLY_PC_FILE_SNAPSHOT_VERIFIED.txt").exists())

    def test_changed_tree_keeps_incomplete_marker(self):
        from backup_v18_e11_sd_reader_to_pc import inventory as original
        count = 0
        def changed(root):
            nonlocal count
            count+=1
            if count == 2:
                (self.sd/"new-file.dat").write_bytes(b"new")
            return original(root)
        with patch("backup_v18_e11_sd_reader_to_pc.inventory",side_effect=changed):
            with self.assertRaisesRegex(ValueError, "source tree changed"):
                copy_and_verify_sd(self.sd,self.out)
        self.assertTrue((self.out/"INCOMPLETE-DO-NOT-RESTORE.txt").exists())
        self.assertFalse((self.out/"READ_ONLY_PC_FILE_SNAPSHOT_VERIFIED.txt").exists())


if __name__ == "__main__":
    unittest.main()
