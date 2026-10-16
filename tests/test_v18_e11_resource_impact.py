#!/usr/bin/env python3
"""Adversarial local-only E11 official updater vs new SD risk tests."""
from __future__ import annotations

import io
from pathlib import Path
import sys
import tarfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_v18_e11_resource_impact import (
    sha, inventory_resources, compare_resource_files, JS_PATH, FAP_PATH,
)


def tar_data(files: dict[str, bytes], *, links=None) -> bytes:
    mem = io.BytesIO()
    with tarfile.open(fileobj=mem, mode="w:gz") as tar:
        for name, data in files.items():
            m = tarfile.TarInfo(name)
            m.size = len(data)
            tar.addfile(m, io.BytesIO(data))
        for name in links or []:
            m = tarfile.TarInfo(name)
            m.type = tarfile.SYMTYPE
            m.linkname = "../danger"
            tar.addfile(m)
    return mem.getvalue()


class E11ResourceImpactTest(unittest.TestCase):
    def setUp(self):
        self.js = b"checked-new-module"
        self.fap = b"checked-new-app"
        self.old = {"assets/baseline.dat": sha(b"abc"),
                    JS_PATH: sha(b"prior-module")}
        self.new = dict(self.old)
        self.new[JS_PATH] = sha(self.js)

    def compare(self):
        return compare_resource_files(self.old, self.new,
                                      expected_js=sha(self.js),
                                      expected_fap=sha(self.fap))

    def test_clean_resources_with_expected_js(self):
        result = self.compare()
        self.assertTrue(result["js_gpio_binary_matches"])
        self.assertEqual(result["modified_count"], 1)
        self.assertFalse(result["device_write_authorized"])
        self.assertFalse(result["labmate_fap_embedded"])

    def test_bundled_labmate_fap_must_match(self):
        self.new[FAP_PATH] = sha(b"fake-fap")
        with self.assertRaisesRegex(ValueError, "LabMate FAP differs"):
            self.compare()
        self.new[FAP_PATH] = sha(self.fap)
        self.assertTrue(self.compare()["labmate_fap_embedded"])

    def test_persistent_labmate_backup_files_must_not_be_in_updater(self):
        self.new["apps_data/labmate/profiles.dat"] = sha(b"data")
        with self.assertRaisesRegex(ValueError, "persistent data"):
            self.compare()

    def test_js_plugin_present_and_exact(self):
        self.new.pop(JS_PATH)
        with self.assertRaisesRegex(ValueError, "native JS GPIO"):
            self.compare()
        self.new[JS_PATH] = sha(b"wrong")
        with self.assertRaisesRegex(ValueError, "JS GPIO binary differs"):
            self.compare()

    def test_other_app_data_changes_honestly_reported(self):
        self.old["apps_data/someone/preferences.ini"] = sha(b"old")
        self.new["apps_data/someone/preferences.ini"] = sha(b"changed")
        r = self.compare()
        self.assertEqual(r["non_js_app_data_changed_count"], 1)
        self.assertFalse(r["device_write_authorized"])

    def test_missing_resource_inventory_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing SD resources"):
            compare_resource_files({}, self.new,
                                   expected_js=sha(self.js),
                                   expected_fap=sha(self.fap))

    def test_tar_inventory_digest(self):
        inv = inventory_resources(tar_data({"./assets/hello.bin": b"hello",
                                            "./apps_data/js_app/plugins/js_gpio.fal": self.js}))
        self.assertEqual(inv[JS_PATH], sha(self.js))
        self.assertEqual(inv["assets/hello.bin"], sha(b"hello"))

    def test_tar_path_traversal_rejected(self):
        for name in ("../escape.bin", "/absolute.bin", "resources/../../outside",
                     "C:/windows.txt", "dir\\evil", "dir//bad"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "unsafe resource"):
                    inventory_resources(tar_data({name: b"bad"}))

    def test_tar_symlink_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-file"):
            inventory_resources(tar_data({"valid": b"x"}, links=["assets/linked"]))

    def test_empty_archive_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty SD resource"):
            inventory_resources(tar_data({}))

    def test_duplicate_tar_resource_member_rejected(self):
        memory = io.BytesIO()
        with tarfile.open(fileobj=memory, mode="w:gz") as tar:
            for i in range(2):
                m = tarfile.TarInfo("apps/data.bin")
                m.size = 1
                tar.addfile(m, io.BytesIO(bytes([i + 1])))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            inventory_resources(memory.getvalue())


if __name__ == "__main__":
    unittest.main()
