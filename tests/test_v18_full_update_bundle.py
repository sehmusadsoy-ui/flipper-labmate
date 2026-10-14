"""Offline negative tests of FULL Momentum firmware update archive gate."""
from __future__ import annotations

import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_v18_full_update_bundle import audit


def tgz_bytes(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as tf:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return output.getvalue()


class FullUpdaterTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.dfu = root / "firmware.dfu"
        self.radio = root / "radio.bin"
        self.pkg = root / "update.tgz"
        self.dfu.write_bytes(b"actual-flipper-firmware")
        self.radio.write_bytes(b"pinned-light-c2-radio")
        self.manifest = "\n".join([
            "Filetype: Flipper firmware upgrade configuration",
            "Version: 2",
            "Target: 7",
            "Firmware: firmware.dfu",
            "Loader: updater.bin",
            "Radio: radio.bin",
            "Radio version: 01 14 00 00 00 00 00",
            "Resources: resources.tgz",
            "OB reference: " + " ".join(["00"] * 128),
            "OB mask: " + " ".join(["00"] * 128),
            "OB write mask: " + " ".join(["00"] * 128),
            "",
        ])
        self.resources = tgz_bytes({"some_resource.txt": b"hello"})
        self.prepare()

    def prepare(self, *, dfu=None, radio=None, manifest=None, extra=None, resources=None):
        names = {
            "firmware.dfu": self.dfu.read_bytes() if dfu is None else dfu,
            "radio.bin": self.radio.read_bytes() if radio is None else radio,
            "updater.bin": b"test-only-stage",
            "update.fuf": (self.manifest if manifest is None else manifest).encode(),
            "resources.tgz": self.resources if resources is None else resources,
        }
        names.update(extra or {})
        files = {"f7-update-test/" + key: data for key, data in names.items()}
        self.pkg.write_bytes(tgz_bytes(files))

    def test_good_full_archive(self):
        result = audit(self.pkg, self.dfu, self.radio)
        self.assertEqual(result["resource_members"], 1)

    def test_wrong_firmware(self):
        self.prepare(dfu=b"wrong")
        with self.assertRaisesRegex(ValueError, "DFU differs"):
            audit(self.pkg, self.dfu, self.radio)

    def test_wrong_radio(self):
        self.prepare(radio=b"wrong")
        with self.assertRaisesRegex(ValueError, "radio differs"):
            audit(self.pkg, self.dfu, self.radio)

    def test_resource_missing(self):
        self.prepare()
        with tarfile.open(self.pkg, "r:gz") as tf:
            other = {m.name: tf.extractfile(m).read() for m in tf if m.isfile() and m.name != "f7-update-test/resources.tgz"}
        self.pkg.write_bytes(tgz_bytes(other))
        with self.assertRaisesRegex(ValueError, "missing radio, SD resources"):
            audit(self.pkg, self.dfu, self.radio)

    def test_wrong_target(self):
        self.prepare(manifest=self.manifest.replace("Target: 7", "Target: 18"))
        with self.assertRaisesRegex(ValueError, "Target"):
            audit(self.pkg, self.dfu, self.radio)

    def test_bad_option_bytes_format(self):
        self.prepare(manifest=self.manifest.replace("OB write mask: " + " ".join(["00"] * 128), "OB write mask: 01"))
        with self.assertRaisesRegex(ValueError, "option-byte"):
            audit(self.pkg, self.dfu, self.radio)

    def test_archive_with_extra_binaries(self):
        self.prepare(extra={"untrusted.bin": b"x"})
        with self.assertRaisesRegex(ValueError, "unexpected"):
            audit(self.pkg, self.dfu, self.radio)

    def test_archive_traversal(self):
        self.prepare(extra={"../../outside": b"x"})
        with self.assertRaisesRegex(ValueError, "unsafe tar path"):
            audit(self.pkg, self.dfu, self.radio)


if __name__ == "__main__":
    unittest.main()
