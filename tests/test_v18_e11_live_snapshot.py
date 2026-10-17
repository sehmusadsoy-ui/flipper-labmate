#!/usr/bin/env python3
"""Mock only: NO real device, actual SD or existing user files."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from snapshot_v18_e11_live_labmate_sd import (
    stage_live_snapshot, check_destination, safe_relative,
    WINDOWS_RESERVED
)


class FakeRead:
    def __init__(self, batches):
        self.batches = list(batches)
    def until(self, prompt):
        if not self.batches:
            raise ValueError("test CLI listing exhausted")
        return self.batches.pop(0)


class FakeStorage:
    CLI_PROMPT = ">: "
    def __init__(self, files, *, changed_after=False, tamper_data=False):
        self.files = dict(files)
        self.changed_after = changed_after
        self.tamper_data = tamper_data
        self.commands = []
        listing = b"".join(
            b"[F] " + name.encode("ascii") + b" " + str(len(data)).encode() + b"b\r\n"
            for name, data in sorted(self.files.items())
        )
        self.read = FakeRead([listing, listing])
        self.listing_count = 0
    def send_and_wait_eol(self, cmd):
        if not cmd.startswith('storage list "/ext/apps_data/labmate"'):
            raise AssertionError("forbidden device command")
        self.commands.append(cmd)
        self.listing_count += 1
    def hash_flipper(self, path):
        assert path.startswith("/ext/apps_data/labmate/")
        key = path[len("/ext/apps_data/labmate/"):]
        self.commands.append("storage md5 only")
        if self.changed_after and self.listing_count > 1:
            return "a" * 32
        return hashlib.md5(self.files[key]).hexdigest()
    def read_file(self, path):
        assert path.startswith("/ext/apps_data/labmate/")
        key = path[len("/ext/apps_data/labmate/"):]
        self.commands.append("storage read_chunks only")
        return b"tampered" if self.tamper_data else self.files[key]


class SnapshotE11Tests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.history = self.root / "old-keep"
        self.history.mkdir()
        (self.history / "log_0041.csv").write_bytes(b"historic")
        (self.history / "log_0050.csv").write_bytes(b"same")
        self.historical_hashes = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in self.history.iterdir()
        }
        self.out = self.root / "new-current-only"
        self.storage = FakeStorage({
            "log_0050.csv": b"same",
            "log_0051.csv": b"new",
            "profiles.bin": b"changed",
        })

    def assert_history_preserved(self):
        for p in self.history.iterdir():
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),
                             self.historical_hashes[p.name])

    def test_full_success_pc_only_and_existing_history_untouched(self):
        result = stage_live_snapshot(self.storage, self.history, self.out)
        self.assertEqual(result["snapshot_files_verified"], 3)
        self.assertEqual(result["new_device_files_preserved"], 2)
        self.assertEqual(result["historical_files_not_on_device"], 1)
        self.assertEqual((self.out / "log_0051.csv").read_bytes(), b"new")
        self.assertFalse((self.out / "INCOMPLETE-DO-NOT-RESTORE.txt").exists())
        self.assertTrue((self.out / "READ_ONLY_SNAPSHOT_VERIFIED.txt").exists())
        manifest = json.loads((self.out / "PC_SNAPSHOT_MANIFEST.json").read_text())
        self.assertFalse(manifest["full_microSD_backup"])
        self.assertFalse(manifest["install_authorized"])
        self.assertEqual(len(manifest["files"]), 3)
        self.assertEqual(manifest["files"]["log_0051.csv"]["sha256_of_pc_readback"],
                         hashlib.sha256(b"new").hexdigest())
        self.assert_history_preserved()
        self.assertEqual(self.storage.listing_count, 2)
        self.assertEqual(sum(cmd == "storage read_chunks only"
                             for cmd in self.storage.commands), 3)
        self.assertFalse(any("write_chunk" in cmd or "remove" in cmd or
                             "format" in cmd for cmd in self.storage.commands))

    def test_refuse_existing_output_before_ever_reading_device(self):
        self.out.mkdir()
        (self.out / "keep").write_bytes(b"old")
        with self.assertRaisesRegex(ValueError, "exists"):
            stage_live_snapshot(self.storage, self.history, self.out)
        self.assertEqual(self.storage.commands, [])
        self.assertEqual((self.out / "keep").read_bytes(), b"old")

    def test_refuse_destination_inside_historic_backup(self):
        with self.assertRaisesRegex(ValueError, "overlaps"):
            check_destination(self.history / "nested", self.history)
        self.assertFalse((self.history / "nested").exists())

    def test_refuse_snapshot_data_tampering_keep_incomplete_marker(self):
        self.storage.tamper_data = True
        with self.assertRaisesRegex(ValueError, "size changed|MD5 changed"):
            stage_live_snapshot(self.storage, self.history, self.out)
        self.assertTrue((self.out / "INCOMPLETE-DO-NOT-RESTORE.txt").exists())
        self.assertFalse((self.out / "READ_ONLY_SNAPSHOT_VERIFIED.txt").exists())
        self.assert_history_preserved()

    def test_refuse_drift_during_snapshot(self):
        self.storage.changed_after = True
        with self.assertRaisesRegex(ValueError, "changed during snapshot"):
            stage_live_snapshot(self.storage, self.history, self.out)
        self.assertTrue((self.out / "INCOMPLETE-DO-NOT-RESTORE.txt").exists())
        self.assertFalse((self.out / "READ_ONLY_SNAPSHOT_VERIFIED.txt").exists())
        self.assert_history_preserved()

    def test_refuse_windows_reserved_files(self):
        for reserved in WINDOWS_RESERVED:
            with self.subTest(reserved=reserved):
                with self.assertRaisesRegex(ValueError, "reserved Windows"):
                    safe_relative(reserved.lower() + ".csv")

    def test_refuse_unsafe_relative_path(self):
        for name in ("", "C:/bad", "/root", "nested\\bad", "bad.", "x/.."):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_relative(name)

    def test_refuse_oversized_device_file_before_pc_write(self):
        self.storage = FakeStorage({"big.dat": b"x" * 10_000_001})
        with self.assertRaisesRegex(ValueError, "unsafe live LabMate file size"):
            stage_live_snapshot(self.storage, self.history, self.out)
        self.assertFalse(self.out.exists())

    def test_refuse_bad_or_empty_live_inventory(self):
        storage = FakeStorage({})
        storage.read = FakeRead([b"Empty"])
        with self.assertRaisesRegex(ValueError, "no readable"):
            stage_live_snapshot(storage, self.history, self.out)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
