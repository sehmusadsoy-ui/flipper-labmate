#!/usr/bin/env python3
"""Fake COM/SD only. Test live-LabMate read-only inventory FAIL-CLOSED."""
from __future__ import annotations

import io
from pathlib import Path
import tempfile
import unittest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_v18_e11_live_labmate_sd import (
    parse_listing, remote_inventory, local_inventory, compare_backups,
)

class FakeRead:
    def __init__(self, replies):
        self.replies = replies
    def until(self, prompt):
        if not self.replies:
            raise AssertionError("unexpected extra CLI read")
        return self.replies.pop(0)

class FakeStorage:
    CLI_PROMPT = ">: "
    def __init__(self, replies, digests):
        self.read = FakeRead(list(replies))
        self.commands = []
        self.digests = digests
    def send_and_wait_eol(self, command):
        self.commands.append(command)
        assert command.startswith('storage list "')
        assert command.endswith('"\r')
    def hash_flipper(self, path):
        self.commands.append('storage md5 "' + path + '"')
        return self.digests[path]

class TestE11LiveLabMateSD(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_exact_parity_with_read_only_flipper_commands(self):
        src = self.root / "copy"
        src.mkdir()
        (src / "log_0050.csv").write_bytes(b"sample")
        (src / "profiles.bin").write_bytes(b"profiles")
        local = local_inventory(src)
        m1, m2 = local["log_0050.csv"][1], local["profiles.bin"][1]
        storage = FakeStorage(
            [b"[F] log_0050.csv 6\r\n[F] profiles.bin 8"],
            {
                "/ext/apps_data/labmate/log_0050.csv": m1,
                "/ext/apps_data/labmate/profiles.bin": m2,
            },
        )
        live = remote_inventory(storage)
        self.assertEqual(compare_backups(live, local)["current_data_backup_parity"], "MATCH")
        self.assertEqual(len(storage.commands), 3)
        self.assertTrue(all(x.startswith("storage list ") or x.startswith("storage md5 ")
                            for x in storage.commands))
        self.assertFalse(any(k in " ".join(storage.commands)
                             for k in ("storage send", "write_chunk",
                                       "remove", "format", "update install")))
    def test_gap_when_historic_logs_absent(self):
        local = {"log_0041.csv": (5, "a"*32), "log_0050.csv": (2, "b"*32)}
        live = {"log_0050.csv": (2, "b"*32)}
        r = compare_backups(live, local)
        self.assertEqual(r["current_data_backup_parity"], "GAP")
        self.assertEqual(r["historical_files_now_absent"], 1)
        self.assertEqual(r["same_path_same_size_md5"], 1)
        self.assertEqual(r["install_authorized"], "NO")

    def test_unbacked_new_csv_is_gap(self):
        r = compare_backups(
            {"log_0050.csv": (8, "b"*32), "log_0051.csv": (9, "c"*32)},
            {"log_0050.csv": (8, "b"*32)}
        )
        self.assertEqual(r["current_data_backup_parity"], "GAP")
        self.assertEqual(r["new_device_files_not_in_backup"], 1)

    def test_changed_file_is_gap(self):
        r = compare_backups(
            {"profiles.bin": (10, "a"*32)},
            {"profiles.bin": (10, "b"*32)}
        )
        self.assertEqual(r["changed_files_not_covered_by_backup"], 1)
        self.assertEqual(r["current_data_backup_parity"], "GAP")

    def test_multiple_nested_directories(self):
        storage = FakeStorage(
            [b"[D] configs\r\n[F] log_0055.csv 2",
             b"[F] app.ini 3"],
            {
                "/ext/apps_data/labmate/log_0055.csv": "a"*32,
                "/ext/apps_data/labmate/configs/app.ini": "b"*32,
            },
        )
        result = remote_inventory(storage)
        self.assertEqual(result["configs/app.ini"], (3, "b"*32))
        self.assertEqual(len(result), 2)

    def test_cli_error_refused_not_silent(self):
        with self.assertRaisesRegex(ValueError, "storage error"):
            parse_listing(b"Storage error: filesystem not ready")

    def test_unrecognized_or_malformed_listing_refused(self):
        for value in (
            b"partial data",
            b"[F] no-size",
            b"[F] file.dat -1",
            b"[F] ../unsafe 123",
            b"[F] file.dat NaN",
            b"[D] \\bad",
            b"[F] log.csv 1\n[F] LOG.csv 1",
            b"Empty\n[F] another.csv 3",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_listing(value)

    def test_bad_md5_refused(self):
        storage = FakeStorage([b"[F] data.bin 2"],
                              {"/ext/apps_data/labmate/data.bin": "INVALID"})
        with self.assertRaisesRegex(ValueError, "MD5"):
            remote_inventory(storage)

    def test_empty_sd_refused(self):
        storage = FakeStorage([b"Empty"], {})
        with self.assertRaisesRegex(ValueError, "no readable"):
            remote_inventory(storage)

    def test_other_sd_path_forbidden(self):
        storage = FakeStorage([], {})
        with self.assertRaisesRegex(ValueError, "only the pinned"):
            remote_inventory(storage, root="/ext")

    def test_local_flat_and_one_labmate_prefix_allowed(self):
        one = self.root / "flat"
        one.mkdir()
        (one / "log_0045.csv").write_bytes(b"x")
        self.assertIn("log_0045.csv", local_inventory(one))
        two = self.root / "nested"
        (two / "labmate").mkdir(parents=True)
        (two / "labmate" / "log_0045.csv").write_bytes(b"x")
        self.assertIn("log_0045.csv", local_inventory(two))

    def test_local_case_collisions_rejected(self):
        folder = self.root / "dupe"
        folder.mkdir()
        (folder / "a.csv").write_bytes(b"a")
        (folder / "A.csv").write_bytes(b"b")
        # On default Windows NTFS a.csv and A.csv are the SAME file.
        # Do not mistake filesystem case-folding for a broken guard.
        if len(list(folder.iterdir())) < 2:
            self.skipTest("filesystem cannot represent distinct case-colliding paths")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            local_inventory(folder)

    def test_local_symlink_rejected(self):
        folder = self.root / "links"
        folder.mkdir()
        (folder / "real.csv").write_bytes(b"x")
        (folder / "alias.csv").symlink_to(folder / "real.csv")
        with self.assertRaisesRegex(ValueError, "unsafe"):
            local_inventory(folder)


if __name__ == "__main__":
    unittest.main()
