"""Native tests for the read-only minimal updater archive integrity gate."""
import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_v18_minimal_update_bundle import check_bundle


class TestMinimalBundle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fw = self.root / "firmware.dfu"
        self.fw.write_bytes(b"TEST-FIRMWARE" * 8)
        self.tgz = self.root / "firmware-update.tgz"
        self.manifest = (
            "Filetype: Flipper firmware upgrade configuration\n"
            "Version: 2\nInfo: dev\nTarget: 7\n"
            "Loader: updater.bin\nFirmware: firmware.dfu\n"
            "Radio: \nResources: \nSplashscreen: \n"
            "OB write mask: 00 00 00 00 00 00 00 00\n"
        )

    def make(self, *, payload=None, manifest=None, extras=None, root="f7-update-test"):
        files = {
            "firmware.dfu": self.fw.read_bytes() if payload is None else payload,
            "updater.bin": b"FAKE-STAGE",
            "update.fuf": (self.manifest if manifest is None else manifest).encode(),
        }
        files.update(extras or {})
        with tarfile.open(self.tgz, "w:gz") as tf:
            for name, data in files.items():
                info = tarfile.TarInfo(root + "/" + name)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))

    def test_good(self):
        self.make()
        check_bundle(self.tgz, self.fw)

    def test_wrong_firmware(self):
        self.make(payload=b"DIFFERENT")
        with self.assertRaisesRegex(ValueError, "differs"):
            check_bundle(self.tgz, self.fw)

    def test_extra_radio(self):
        self.make(extras={"radio.bin": b"RADIO"})
        with self.assertRaisesRegex(ValueError, "minimal updater"):
            check_bundle(self.tgz, self.fw)

    def test_radio_field(self):
        self.make(manifest=self.manifest.replace("Radio: \n", "Radio: radio.bin\n"))
        with self.assertRaisesRegex(ValueError, "Radio"):
            check_bundle(self.tgz, self.fw)

    def test_option_byte_write(self):
        self.make(manifest=self.manifest.replace(
            "OB write mask: 00", "OB write mask: 01"))
        with self.assertRaisesRegex(ValueError, "option-byte"):
            check_bundle(self.tgz, self.fw)

    def test_wrong_target(self):
        self.make(manifest=self.manifest.replace("Target: 7", "Target: 5"))
        with self.assertRaisesRegex(ValueError, "target"):
            check_bundle(self.tgz, self.fw)

    def test_path_traversal(self):
        self.make(extras={"../../bad": b"X"})
        with self.assertRaisesRegex(ValueError, "unsafe"):
            check_bundle(self.tgz, self.fw)


if __name__ == "__main__":
    unittest.main()
