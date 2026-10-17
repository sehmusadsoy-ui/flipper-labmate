#!/usr/bin/env python3
"""Test strict, deterministic FAP-excluded updater derivative (NEVER DEVICE)."""
from __future__ import annotations

import io
from pathlib import Path
import sys
import tarfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_v18_e11_resource_impact import (
    FAP_PATH, JS_PATH, sha, inventory_resources
)
from derive_v18_e11_split_review import (
    tarball, split_resources, derive_full_review, ROOT, FILES, WARNING
)


class DerivedSplitReviewTest(unittest.TestCase):
    def setUp(self):
        self.fap = b"test-only-labmate-app"
        self.js = b"test-only-javascript-native-module"
        self.dfu = b"test-only-patched-firmware"
        self.radio = b"test-only-pinned-radio"
        self.resources = tarball([
            ("apps", None),
            ("apps/Tools", None),
            (FAP_PATH, self.fap),
            ("apps_data", None),
            ("apps_data/js_app", None),
            ("apps_data/js_app/plugins", None),
            (JS_PATH, self.js),
            ("assets/legacy.bin", b"keep bytes unchanged"),
        ])
        self.full = {name: ("placeholder:" + name).encode() for name in FILES}
        self.full["firmware.dfu"] = self.dfu
        self.full["radio.bin"] = self.radio
        self.full["resources.tar.gz"] = self.resources
        self.full["update.fuf"] = b"Resources: resources.tar.gz\n"

    def split(self, *, fap=None, js=None):
        return split_resources(self.resources,
                               expected_fap=sha(self.fap) if fap is None else fap,
                               expected_js=sha(self.js) if js is None else js)

    def derive(self):
        return derive_full_review(
            self.full,
            expected_fap=sha(self.fap),
            expected_js=sha(self.js),
            expected_dfu=sha(self.dfu),
            expected_radio=sha(self.radio),
        )

    def test_future_split_review_readme_warns_of_real_exitfix_removal(self):
        for required in (
            "REAL COM7 old /ext/Manifest",
            "apps/Tools/labmate.fap",
            "SPLIT AS EXITFIX-PRESERVING TRIAL REJECTED",
            "DO NOT FLASH OR INSTALL",
        ):
            with self.subTest(required=required):
                self.assertIn(required, WARNING)

    def test_exact_one_fap_resource_removed_only(self):
        original = inventory_resources(self.resources)
        split = inventory_resources(self.split())
        self.assertNotIn(FAP_PATH, split)
        self.assertEqual(split[JS_PATH], sha(self.js))
        self.assertEqual(set(original) - set(split), {FAP_PATH})
        self.assertEqual({k: v for k, v in original.items() if k != FAP_PATH}, split)

    def test_split_tar_reproducible_deterministically(self):
        self.assertEqual(self.split(), self.split())

    def test_full_derivative_preserves_firmware_radio_manifest_and_all_other_files(self):
        result = self.derive()
        with tarfile.open(fileobj=io.BytesIO(result), mode="r:gz") as tgz:
            files = {m.name: tgz.extractfile(m).read()
                     for m in tgz if m.isfile()}
        self.assertEqual(set(files), {ROOT + "/" + name for name in FILES})
        for name in FILES:
            if name != "resources.tar.gz":
                self.assertEqual(files[ROOT + "/" + name], self.full[name])
        resources = inventory_resources(files[ROOT + "/resources.tar.gz"])
        self.assertNotIn(FAP_PATH, resources)
        self.assertEqual(resources[JS_PATH], sha(self.js))
        self.assertEqual(result, self.derive())

    def test_wrong_app_fingerprint_refused(self):
        with self.assertRaisesRegex(ValueError, "FAP SHA256"):
            self.split(fap=sha(b"wrong"))

    def test_wrong_js_fingerprint_refused(self):
        with self.assertRaisesRegex(ValueError, "JS GPIO"):
            self.split(js=sha(b"wrong"))

    def test_missing_app_refused(self):
        self.resources = tarball([(JS_PATH, self.js), ("assets/k", b"exists")])
        with self.assertRaisesRegex(ValueError, "exactly one"):
            self.split()

    def test_duplicate_app_member_refused(self):
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w:gz") as tf:
            for path, data in ((FAP_PATH, self.fap),
                               (FAP_PATH, self.fap),
                               (JS_PATH, self.js)):
                m = tarfile.TarInfo(path)
                m.size = len(data)
                tf.addfile(m, io.BytesIO(data))
        self.resources = archive.getvalue()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.split()

    def test_unsafe_nested_member_refused(self):
        self.resources = tarball([(FAP_PATH, self.fap), (JS_PATH, self.js),
                                  ("assets/not-empty", b"x")])
        # Use a hand-crafted TAR since the safe tarball() itself rejects bad paths.
        mem = io.BytesIO()
        with tarfile.open(fileobj=mem, mode="w:gz") as tf:
            for name, data in ((FAP_PATH, self.fap), (JS_PATH, self.js),
                               ("../unsafe", b"X")):
                m = tarfile.TarInfo(name)
                m.size = len(data)
                tf.addfile(m, io.BytesIO(data))
        self.resources = mem.getvalue()
        with self.assertRaisesRegex(ValueError, "unsafe"):
            self.split()

    def test_unsupported_updater_member_set_refused(self):
        self.full.pop("updater.bin")
        with self.assertRaisesRegex(ValueError, "wrong source updater"):
            self.derive()


if __name__ == "__main__":
    unittest.main()
