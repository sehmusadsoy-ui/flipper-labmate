#!/usr/bin/env python3
"""Host-only negative/positive model tests: NO Flipper serial or deletion."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cleanup_v18_demo_faps import classify, shortlist, apply


class FakeStorage:
    def __init__(self):
        self.removed = []

    def hash_flipper(self, path):
        if path != "/ext/apps/Tools/labmate.fap":
            raise AssertionError("test must never hash arbitrary apps")
        return "f" * 32

    def remove(self, path):
        self.removed.append(path)


class DemoCleanupTests(unittest.TestCase):
    def test_known_busy_probe(self):
        self.assertTrue(classify("labmate_busydiag.fap"))
        self.assertTrue(classify("labmate_busy_probe.fap"))

    def test_demo_filename_variants(self):
        self.assertTrue(classify("labmate_ui_demo.fap"))
        self.assertTrue(classify("labmate_scope_ui_demo.fap"))
        self.assertTrue(classify("LabMate-2-UI-Demo.FAP"))

    def test_main_fap_always_protected(self):
        self.assertFalse(classify("labmate.fap"))
        self.assertFalse(classify("LabMate.FAP"))

    def test_non_labmate_apps_protected(self):
        self.assertFalse(classify("KeyCopier.fap"))
        self.assertFalse(classify("scope_demo.fap"))
        self.assertFalse(classify("labmate_uart.fap"))
        self.assertFalse(classify("labmate.scope.fap"))

    def test_path_traversal_and_other_extensions_rejected(self):
        for name in ("../labmate_demo.fap", "labmate_demo.fap.bak",
                     "labmate_demo/evil.fap", "labmate_demo.fap\r",
                     "labmate_demo.fap;format"):
            self.assertFalse(classify(name), name)

    def test_fails_closed_for_too_many_candidates(self):
        with self.assertRaisesRegex(ValueError, "more than three"):
            shortlist({("labmate_demo_%d.fap" % i): 12 for i in range(4)})

    def test_fails_closed_for_zero_or_oversized_faps(self):
        with self.assertRaisesRegex(ValueError, "unexpectedly"):
            shortlist({"labmate_demo.fap": 0})
        with self.assertRaisesRegex(ValueError, "unexpectedly"):
            shortlist({"labmate_demo.fap": 4 * 1024 * 1024 + 1})

    def test_exact_selection_only(self):
        files = {"labmate.fap": 95000, "KeyCopier.fap": 4000,
                 "labmate_busydiag.fap": 8000, "labmate_ui_demo.fap": 9000}
        self.assertEqual(set(shortlist(files)), {
            "labmate_busydiag.fap", "labmate_ui_demo.fap"
        })

    def test_empty_candidates_never_delete(self):
        remote = FakeStorage()
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(apply(remote, {}, {"labmate.fap": 100},
                                   Path(folder) / "unused", "f" * 32), [])
            self.assertFalse(remote.removed)

    def test_existing_backup_destination_refused(self):
        remote = FakeStorage()
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "new PC directory"):
                apply(remote, {"labmate_demo.fap": 3}, {"labmate.fap": 10},
                      Path(folder), "f" * 32)
        self.assertFalse(remote.removed)

    def test_decline_after_backup_never_removes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fresh"
            remote = FakeStorage()
            listing = {"labmate.fap": 10, "labmate_demo.fap": 6}
            with patch("cleanup_v18_demo_faps._md5", return_value="a" * 32), \
                 patch("cleanup_v18_demo_faps._read_to_pc", side_effect=make_copy), \
                 patch("cleanup_v18_demo_faps.list_tools", return_value=listing):
                deleted = apply(remote, {"labmate_demo.fap": 6}, listing, path,
                                "f" * 32, confirm=lambda prompt: "NO")
            self.assertEqual(deleted, [])
            self.assertTrue((path / "DEMO_BACKUP_MANIFEST.json").is_file())
            self.assertEqual(remote.removed, [])

    def test_verified_backups_then_exact_file_remove(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fresh"
            remote = FakeStorage()
            chosen = {"labmate_busydiag.fap": 6, "labmate_ui_demo.fap": 6}
            listing = {"labmate.fap": 10, "KeyCopier.fap": 12, **chosen}
            after = {"labmate.fap": 10, "KeyCopier.fap": 12}
            with patch("cleanup_v18_demo_faps._md5", return_value="a" * 32), \
                 patch("cleanup_v18_demo_faps._read_to_pc", side_effect=make_copy), \
                 patch("cleanup_v18_demo_faps.list_tools", side_effect=[listing, after]):
                deleted = apply(remote, chosen, listing, path, "f" * 32,
                                confirm=lambda prompt: "SIL-DEMO-2")
            self.assertEqual(set(deleted), set(chosen))
            self.assertEqual(set(remote.removed), {
                "/ext/apps/Tools/labmate_busydiag.fap",
                "/ext/apps/Tools/labmate_ui_demo.fap",
            })
            self.assertTrue((path / "DEMO_BACKUP_MANIFEST.json").is_file())
            self.assertTrue((path / "labmate_ui_demo.fap").is_file())

    def test_inventory_changes_before_delete_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            remote = FakeStorage()
            chosen = {"labmate_demo.fap": 6}
            listing = {"labmate.fap": 10, **chosen}
            with patch("cleanup_v18_demo_faps._md5", return_value="a" * 32), \
                 patch("cleanup_v18_demo_faps._read_to_pc", side_effect=make_copy), \
                 patch("cleanup_v18_demo_faps.list_tools", return_value={"labmate.fap": 10}):
                with self.assertRaisesRegex(ValueError, "changed before deletion"):
                    apply(remote, chosen, listing, Path(folder) / "fresh",
                          "f" * 32, confirm=lambda _: "SIL-DEMO-1")
            self.assertFalse(remote.removed)


def make_copy(storage, source, size, path):
    # Synthetic bytes; never touch Flipper or user files.
    path.write_bytes(b"z" * size)
    return "a" * 32, "b" * 64


if __name__ == "__main__":
    unittest.main()
