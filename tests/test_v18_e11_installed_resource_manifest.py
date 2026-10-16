#!/usr/bin/env python3
"""No-device scenarios for real firmware updater old-manifest cleanup risk."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "scripts"))
sys.path.insert(0, str(root / "tests"))
from audit_v18_e11_installed_resource_manifest import (
    parse_old_manifest, read_live_manifest, path_ok
)
from test_v18_e11_usb_sd_backup import FakeStorage


def manifest(*, fap=True, labmate_data=True) -> bytes:
    entries = [
        b"V:0",
        b"T:1760000000",
        b"D:apps",
        b"D:apps/Tools",
        b"D:apps_data",
        b"D:apps_data/labmate",
        b"D:apps_data/Other App",
        b"F:" + b"a" * 32 + b":10:apps/Tools/another.fap",
        b"F:" + b"b" * 32 + b":14:apps_data/Other App/settings.cfg",
    ]
    if fap:
        entries.append(b"F:" + b"c" * 32 + b":45123:apps/Tools/labmate.fap")
    if labmate_data:
        entries.append(b"F:" + b"d" * 32 + b":12:apps_data/labmate/history.csv")
    entries.append(b"F:" + b"e" * 32 + b":1:assets/config.ini")
    return b"\n".join(entries) + b"\n"


class E11InstalledResourceManifestTest(unittest.TestCase):
    def test_old_manifest_lists_exitfix_fap_cleanup_risk(self):
        r = parse_old_manifest(manifest(fap=True))
        self.assertEqual(r["old_cleanup_lists_installed_labmate_fap"], "YES")
        self.assertEqual(r["old_cleanup_labmate_data_files"], 1)
        self.assertEqual(r["old_cleanup_non_labmate_apps_data_files"], 1)
        self.assertEqual(r["split_updater_guarantees_exitfix_survival"], "NO")
        self.assertEqual(r["trial_write_authorized"], "NO")

    def test_fap_not_listed_is_not_a_survival_proof(self):
        r = parse_old_manifest(manifest(fap=False))
        self.assertEqual(r["old_cleanup_lists_installed_labmate_fap"], "NO")
        self.assertEqual(r["split_updater_guarantees_exitfix_survival"], "NO")
        self.assertEqual(r["old_cleanup_app_fap_files"], 1)

    def test_no_labmate_userdata_cleanup_when_not_listed(self):
        r = parse_old_manifest(manifest(labmate_data=False))
        self.assertEqual(r["old_cleanup_labmate_data_files"], 0)

    def test_manifest_with_spaces_and_non_ascii_paths_stays_private(self):
        body = manifest() + b"F:" + b"f" * 32 + b":0:apps_data/caf\xc3\xa9/private settings.dat\n"
        r = parse_old_manifest(body)
        self.assertEqual(r["old_cleanup_non_labmate_apps_data_files"], 2)
        self.assertNotIn("private settings", str(r))
        self.assertNotIn("café", str(r))

    def test_same_case_folded_duplicate_file_refused(self):
        data = manifest() + b"F:" + b"f" * 32 + b":14:apps/TOOLS/LABMATE.fap\n"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_old_manifest(data)

    def test_corrupt_manifest_entries_never_count_as_pass(self):
        for item in (
            b"F:" + b"a" * 31 + b":12:apps/fap",
            b"F:" + b"a" * 32 + b":4294967296:apps/file",
            b"F:" + b"a" * 32 + b":2:../etc",
            b"F:" + b"a" * 32 + b":2:/ext/private",
            b"F:" + b"a" * 32 + b":2:apps/x\x00bad",
            b"F:" + b"a" * 32 + b":2:apps/x\\bad",
            b"F:" + b"a" * 32 + b":2:apps/x\n\n",
            b"F:" + b"a" * 32 + b":2:apps/:bad",
            b"D:../../unsafe",
            b"UNKNOWN:manifest-format",
        ):
            with self.subTest(entry=item), self.assertRaises(ValueError):
                parse_old_manifest(manifest() + item + b"\n")

    def test_duplicate_or_wrong_momentum_metadata_refused(self):
        baseline = manifest()
        for bad in (
            baseline + b"V:0\n",
            baseline + b"T:1760000001\n",
            baseline.replace(b"V:0", b"V:7"),
            baseline.replace(b"T:1760000000", b"T:unknown"),
            baseline.replace(b"V:0\n", b""),
            baseline.replace(b"T:1760000000\n", b""),
        ):
            with self.subTest(bad=bad[:24]), self.assertRaises(ValueError):
                parse_old_manifest(bad)

    def test_reject_empty_or_implausibly_short_manifest(self):
        for content in (b"", b"V:1\n", b"D:apps\n", b"F:" + b"a" * 32 + b":0:apps/x\n"):
            with self.subTest(content=content), self.assertRaises(ValueError):
                parse_old_manifest(content)

    def test_validate_opaque_resource_components(self):
        self.assertEqual(path_ok(b"apps/Tools/labmate.fap"), b"apps/tools/labmate.fap")
        self.assertEqual(path_ok(b"apps_data/Other App/", directory=True),
                         b"apps_data/other app")
        for x in (b"foo//bar", b".", b"foo/../x", b"C:/x", b"/ext/apps",
                  b"foo/\tbar", b"apps\\bad"):
            with self.subTest(x=x), self.assertRaises(ValueError):
                path_ok(x)

    def test_real_binary_transfer_protocol_mock_is_read_only(self):
        data = manifest(fap=True)
        storage = FakeStorage({b"/ext/Manifest": data})
        recovered, screen = read_live_manifest(storage)
        self.assertEqual(data, recovered)
        self.assertEqual(screen, hashlib.md5(data).hexdigest())
        trace = storage.port.trace
        commands = [entry for entry in trace if entry != b"read-transfer-handshake"]
        self.assertEqual(sum(b"read_chunks" in c for c in commands), 1)
        self.assertEqual(sum(b"storage md5" in c for c in commands), 2)
        self.assertTrue(all(c.startswith((b"storage md5 ", b"storage read_chunks "))
                            for c in commands))
        self.assertFalse(any(b"write_chunk" in c or b"storage remove" in c
                             or b"update install" in c for c in commands))

    def test_changed_source_manifest_md5_refused(self):
        storage = FakeStorage({b"/ext/Manifest": manifest()})
        storage.port.sabotage_md5 = True
        with self.assertRaisesRegex(ValueError, "changed or USB"):
            read_live_manifest(storage)


if __name__ == "__main__":
    unittest.main()
