"""No-device tests for the fail-closed read-only v1.9 review bundle gate."""
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_v19_review_bundle import FAP_NAME, MOMENTUM_BASE, ReviewError, verify_bundle  # noqa: E402

SHA = "a" * 40
README = b"LabMate: E11 exact patched Momentum ABI ONLY. NOT authorized for FAP installation."


def fake_elf():
    # Syntactically ARM ELF; deliberately NOT an executable FAP. This tests
    # container/publisher-metadata rejection, not binary execution.
    b = bytearray(64)
    b[:6] = b"\x7fELF\x01\x01"
    b[18:20] = (40).to_bytes(2, "little")
    return bytes(b)


def contents():
    elf = fake_elf()
    return {
        FAP_NAME: elf,
        "SHA256SUMS.txt": f"{hashlib.sha256(elf).hexdigest()}  {FAP_NAME}\n".encode(),
        "PROVENANCE.txt": f"SOURCE_SHA={SHA}\nMOMENTUM_BASE={MOMENTUM_BASE}\nGITHUB_RUN_ID=123456\n".encode(),
        "READ_ME_FIRST.txt": README,
    }


class BundleReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)

    def write_dir(self, members):
        sub = self.dir / "review"
        sub.mkdir(exist_ok=True)
        for name, blob in members.items():
            (sub / name).write_bytes(blob)
        return sub

    def write_zip(self, members):
        target = self.dir / "review.zip"
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name, blob in members.items():
                z.writestr(name, blob)
        return target

    def test_valid_folder_and_zip_review(self):
        self.assertEqual(verify_bundle(self.write_dir(contents()), SHA)[0], 64)
        self.assertEqual(verify_bundle(self.write_zip(contents()), SHA)[0], 64)

    def test_changed_fap_bytes_rejected(self):
        m = contents()
        m[FAP_NAME] = m[FAP_NAME][:-1] + b"X"
        with self.assertRaises(ReviewError):
            verify_bundle(self.write_zip(m), SHA)

    def test_stale_source_rejected(self):
        with self.assertRaises(ReviewError):
            verify_bundle(self.write_zip(contents()), "b" * 40)

    def test_wrong_firmware_base_rejected(self):
        m = contents()
        m["PROVENANCE.txt"] = m["PROVENANCE.txt"].replace(
            MOMENTUM_BASE.encode(), b"c" * 40)
        with self.assertRaises(ReviewError):
            verify_bundle(self.write_zip(m), SHA)

    def test_duplicate_member_rejected(self):
        import warnings
        z = self.dir / "duplicate.zip"
        m = contents()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(z, "w") as arc:
                for name, blob in m.items():
                    arc.writestr(name, blob)
                arc.writestr(FAP_NAME, m[FAP_NAME])
        with self.assertRaises(ReviewError):
            verify_bundle(z, SHA)

    def test_nested_member_rejected(self):
        m = contents()
        m["nested/" + FAP_NAME] = m.pop(FAP_NAME)
        with self.assertRaises(ReviewError):
            verify_bundle(self.write_zip(m), SHA)

    def test_unsupported_arm_architecture_rejected(self):
        m = contents()
        binary = bytearray(m[FAP_NAME])
        binary[18:20] = (62).to_bytes(2, "little")
        m[FAP_NAME] = bytes(binary)
        m["SHA256SUMS.txt"] = (
            f"{hashlib.sha256(m[FAP_NAME]).hexdigest()}  {FAP_NAME}\n".encode())
        with self.assertRaises(ReviewError):
            verify_bundle(self.write_zip(m), SHA)

    def test_missing_no_install_warning_rejected(self):
        m = contents()
        m["READ_ME_FIRST.txt"] = b"Ready for installation"
        with self.assertRaises(ReviewError):
            verify_bundle(self.write_zip(m), SHA)

    def test_extra_file_rejected(self):
        m = contents()
        m["untrusted.sh"] = b"hello"
        with self.assertRaises(ReviewError):
            verify_bundle(self.write_zip(m), SHA)

    def test_duplicate_provenance_rejected(self):
        m = contents()
        m["PROVENANCE.txt"] += f"SOURCE_SHA={SHA}\n".encode()
        with self.assertRaises(ReviewError):
            verify_bundle(self.write_zip(m), SHA)

    def test_bad_source_sha_parameter_rejected(self):
        with self.assertRaises(ReviewError):
            verify_bundle(self.write_zip(contents()), "123")


if __name__ == "__main__":
    unittest.main()
