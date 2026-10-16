#!/usr/bin/env python3
"""Synthetic adversarial tests for STRICTLY LOCAL, no-device E11 staging."""
from __future__ import annotations

import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from stage_v18_e11_review_only import FILES, ROOT, inspect_updater, write_review_stage, require_isolated_output
from preflight_v18_e11_local import ARTIFACTS
import hashlib


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def tar_bytes(contents: dict[str, bytes], *, symlink=False, duplicate=False) -> bytes:
    memory = io.BytesIO()
    with tarfile.open(fileobj=memory, mode="w:gz") as tf:
        d = tarfile.TarInfo(ROOT)
        d.type = tarfile.DIRTYPE
        tf.addfile(d)
        for name, payload in contents.items():
            entry = tarfile.TarInfo(name)
            entry.size = len(payload)
            tf.addfile(entry, io.BytesIO(payload))
        if duplicate:
            entry = tarfile.TarInfo(ROOT + "/firmware.dfu")
            entry.size = 1
            tf.addfile(entry, io.BytesIO(b"x"))
        if symlink:
            entry = tarfile.TarInfo(ROOT + "/intruder")
            entry.type = tarfile.SYMTYPE
            entry.linkname = "../../private"
            tf.addfile(entry)
    return memory.getvalue()


class E11ReviewStageTest(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.tgz = self.root / "sample.tgz"
        self.dfu = b"synthetic-firmware-e11"
        self.radio = b"synthetic-official-radio"
        self.payloads = {ROOT + "/" + name: (self.dfu if name == "firmware.dfu"
            else self.radio if name == "radio.bin"
            else ("synthetic-" + name).encode("ascii"))
                         for name in FILES}
        self.tgz.write_bytes(tar_bytes(self.payloads))

    def checked(self):
        return inspect_updater(
            self.tgz, expected_dfu=digest(self.dfu),
            expected_radio=digest(self.radio))

    def test_positive_strict_stage_review_only(self):
        files = self.checked()
        self.assertEqual(set(files), set(FILES))
        dst = self.root / "brand-new-stage"
        result = write_review_stage(dst, files)
        self.assertEqual(result, dst / ROOT)
        self.assertEqual((result / "firmware.dfu").read_bytes(), self.dfu)
        self.assertIn("DO NOT FLASH", (dst / "STAGING_REVIEW_ONLY.txt").read_text())
        self.assertEqual(set(p.name for p in result.iterdir()), set(FILES))
        self.assertEqual(len(list(dst.rglob("*.fuf"))), 1)

    def test_refuse_to_overwrite_existing_stage(self):
        dst = self.root / "existing-stage"
        dst.mkdir()
        (dst / "keep.txt").write_text("preserve")
        with self.assertRaisesRegex(ValueError, "exists"):
            write_review_stage(dst, self.checked())
        self.assertEqual((dst / "keep.txt").read_text(), "preserve")

    def test_refuse_missing_member(self):
        self.payloads.pop(ROOT + "/updater.bin")
        self.tgz.write_bytes(tar_bytes(self.payloads))
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.checked()

    def test_refuse_nested_path_traversal(self):
        self.payloads[ROOT + "/../bad"] = b"oops"
        self.tgz.write_bytes(tar_bytes(self.payloads))
        with self.assertRaisesRegex(ValueError, "unexpected"):
            self.checked()

    def test_refuse_extra_member(self):
        self.payloads[ROOT + "/extra"] = b"oops"
        self.tgz.write_bytes(tar_bytes(self.payloads))
        with self.assertRaisesRegex(ValueError, "unexpected"):
            self.checked()

    def test_refuse_archive_symlink(self):
        self.tgz.write_bytes(tar_bytes(self.payloads, symlink=True))
        with self.assertRaisesRegex(ValueError, "unexpected"):
            self.checked()

    def test_refuse_duplicate_updater_file(self):
        self.tgz.write_bytes(tar_bytes(self.payloads, duplicate=True))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.checked()

    def test_refuse_changed_dfu(self):
        self.payloads[ROOT + "/firmware.dfu"] = b"mutated"
        self.tgz.write_bytes(tar_bytes(self.payloads))
        with self.assertRaisesRegex(ValueError, "firmware.dfu"):
            self.checked()

    def test_refuse_changed_radio(self):
        self.payloads[ROOT + "/radio.bin"] = b"wrong-radio"
        self.tgz.write_bytes(tar_bytes(self.payloads))
        with self.assertRaisesRegex(ValueError, "radio.bin"):
            self.checked()

    def test_refuse_missing_local_archive(self):
        self.tgz.unlink()
        with self.assertRaisesRegex(ValueError, "missing or linked"):
            self.checked()

    def test_refuse_unsafe_file_name_or_set(self):
        self.assertRaisesRegex(ValueError, "missing/extra",
                               write_review_stage, self.root / "other",
                               {"firmware.dfu": b"x"})
        self.assertFalse((self.root / "other").exists())

    def test_refuse_stage_inside_any_verified_input(self):
        for name in ("candidate", "rollback", "data"):
            protected = self.root / name
            protected.mkdir()
            with self.assertRaisesRegex(ValueError, "protected"):
                require_isolated_output(
                    protected / "new-review",
                    (protected,),
                )
            self.assertFalse((protected / "new-review").exists())

    def test_refuse_linked_output_parent(self):
        target = self.root / "real"
        target.mkdir()
        alias = self.root / "alias"
        alias.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "parent"):
            write_review_stage(alias / "new-stage", self.checked())
        self.assertFalse((target / "new-stage").exists())


if __name__ == "__main__":
    unittest.main()
