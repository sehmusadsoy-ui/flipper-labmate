#!/usr/bin/env python3
"""Pure synthetic post-update identity/manifest checks. Never touches USB."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import sys
import tarfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_v18_e11_postupdate_readonly import REMOTE, evaluate, extract_new_manifest


class PostUpdateReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.info = b"hardware_model: Flipper Zero\r\nfirmware.version: mntm-dev\r\nfirmware.commit.hash: d3f89dfe\r\n"
        self.hashes = {name: hashlib.md5(name.encode()).hexdigest() for name in REMOTE}

    def test_exact_resources_and_label(self):
        evaluate(self.info, dict(self.hashes), dict(self.hashes))

    def test_fap_mismatch(self):
        modified = dict(self.hashes)
        modified["E11_APP"] = "0" * 32
        with self.assertRaisesRegex(ValueError, "E11_APP"):
            evaluate(self.info, modified, self.hashes)

    def test_js_mismatch(self):
        modified = dict(self.hashes)
        modified["E11_JS_GPIO"] = "0" * 32
        with self.assertRaisesRegex(ValueError, "E11_JS_GPIO"):
            evaluate(self.info, modified, self.hashes)

    def test_manifest_mismatch(self):
        modified = dict(self.hashes)
        modified["E11_NEW_MANIFEST"] = "0" * 32
        with self.assertRaisesRegex(ValueError, "E11_NEW_MANIFEST"):
            evaluate(self.info, modified, self.hashes)

    def test_old_firmware_label_rejected(self):
        with self.assertRaisesRegex(ValueError, "unexpected firmware"):
            evaluate(self.info.replace(b"mntm-dev", b"mntm-012"), self.hashes, self.hashes)

    def test_wrong_base_rejected(self):
        with self.assertRaisesRegex(ValueError, "unexpected firmware"):
            evaluate(self.info.replace(b"d3f89dfe", b"12345678"), self.hashes, self.hashes)

    def test_incomplete_md5(self):
        with self.assertRaisesRegex(ValueError, "incomplete exact"):
            evaluate(self.info, {}, self.hashes)

    def test_storage_error_rejected(self):
        modified = dict(self.hashes)
        modified["E11_APP"] = "Storage error"
        with self.assertRaisesRegex(ValueError, "invalid resource MD5"):
            evaluate(self.info, modified, self.hashes)

    def test_invalid_utf8_report(self):
        with self.assertRaises(UnicodeDecodeError):
            evaluate(b"\xff", self.hashes, self.hashes)

    def test_single_tar_manifest(self):
        mem = io.BytesIO()
        with tarfile.open(fileobj=mem, mode="w:gz") as tf:
            contents = b"V:0\nT:1760000000\n"
            i = tarfile.TarInfo("Manifest")
            i.size = len(contents)
            tf.addfile(i, io.BytesIO(contents))
        self.assertEqual(extract_new_manifest(mem.getvalue()), contents)

    def test_duplicate_manifest_rejected(self):
        mem = io.BytesIO()
        with tarfile.open(fileobj=mem, mode="w:gz") as tf:
            for name in ("Manifest", "./Manifest"):
                contents = b"V:0\n"
                i = tarfile.TarInfo(name)
                i.size = len(contents)
                tf.addfile(i, io.BytesIO(contents))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            extract_new_manifest(mem.getvalue())

    def test_missing_manifest_rejected(self):
        mem = io.BytesIO()
        with tarfile.open(fileobj=mem, mode="w:gz") as tf:
            contents = b"read only"
            i = tarfile.TarInfo("README")
            i.size = len(contents)
            tf.addfile(i, io.BytesIO(contents))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            extract_new_manifest(mem.getvalue())


if __name__ == "__main__":
    unittest.main()
