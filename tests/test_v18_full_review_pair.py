#!/usr/bin/env python3
"""Positive + adversarial tests for the READ-ONLY full v1.8 review pair."""
from __future__ import annotations
import hashlib
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_v18_full_review_pair import verify, PIN, MNTM012, BINARIES

SOURCE = "349d717f6cde7d1a117edea0db0058e9f2a5748f"
RUN = 38955881504
RADIO = b"test-only-radio-binary"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def archive(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, payload in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            tf.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


def tgz(dfu: bytes, radio: bytes) -> bytes:
    resources = archive({"apps_data/js_app/plugins/js_gpio.fal": b"JS"})
    ob = " ".join(["00"] * 128)
    manifest = "\n".join([
        "Target: 7",
        "Firmware: firmware.dfu",
        "Loader: updater.bin",
        "Radio: radio.bin",
        "Resources: resources.tar.gz",
        "Radio version: 1",
        "OB reference: " + ob,
        "OB mask: " + ob,
        "OB write mask: " + ob,
    ]).encode()
    return archive({
        "f7-update-test/firmware.dfu": dfu,
        "f7-update-test/updater.bin": b"UPDATER",
        "f7-update-test/update.fuf": manifest,
        "f7-update-test/radio.bin": radio,
        "f7-update-test/resources.tar.gz": resources,
    })


def checksum(directory: Path):
    (directory / "SHA256SUMS.txt").write_text("".join(
        sha((directory / name).read_bytes()) + "  " + name + "\n"
        for name in BINARIES
    ), encoding="utf-8")


class FullReviewPairTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        payloads = {
            "labmate.fap": b"ONE-INTEGRATED-LABMATE",
            "js_gpio.module": b"JS",
            "firmware.dfu": b"TEST-DFU",
            "firmware-full-update.tgz": tgz(b"TEST-DFU", RADIO),
        }
        for name, data in payloads.items():
            (self.directory / name).write_bytes(data)
        checksum(self.directory)
        (self.directory / "PROVENANCE.txt").write_text(
            f"LabMate commit: {SOURCE}\n"
            f"E11 firmware diff SHA256: {'d' * 64}\n"
            "Native JS GPIO plugin source: applications/system/js_app/modules/js_gpio.c (E11 patched)\n"
            f"Momentum base: {PIN}\n"
            f"Installed Momentum012 source: {MNTM012}\n"
            f"Actions run: {RUN}\n",
            encoding="utf-8",
        )
        (self.directory / "READ_ME_FIRST.txt").write_text(
            "NOT A RELEASE. DO NOT FLASH. NO PHYSICAL ACCEPTANCE/RESTORE TEST.\n"
            "Never mix this matched FAP with unpatched Momentum firmware.\n",
            encoding="utf-8",
        )

    def checked(self, *, source=SOURCE, run=RUN, radio=RADIO):
        return verify(self.directory, source, run, expected_radio_sha256=sha(radio))

    def assert_refused(self, needle: str, **kwargs):
        with self.assertRaisesRegex(ValueError, needle):
            self.checked(**kwargs)

    def test_full_firmware_ci_invokes_verifier_with_exact_arguments(self):
        """Catch YAML/Bash accidental double-backslash line continuation."""
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/check-v18-full-012-upgrade-package.yml"
                    ).read_text("utf-8")
        begin = workflow.index("      - name: Independently re-verify FULL review pair")
        end = workflow.index("      - name: Archive for review ONLY", begin)
        step = workflow[begin:end]
        expected = ('python3 labmate/scripts/verify_v18_full_review_pair.py '
                    'dev-full-candidate --expected-source "$GITHUB_SHA" '
                    '--expected-run "$GITHUB_RUN_ID"')
        self.assertIn(expected, step)
        self.assertNotIn("\\", step, "Shell backslash regression in verifier CLI")

    def test_valid_exact_pair(self):
        result = self.checked()
        self.assertEqual(result["Actions run"], str(RUN))
        self.assertEqual(result["labmate.fap"], sha(b"ONE-INTEGRATED-LABMATE"))

    def test_binary_tamper_no_recognition(self):
        (self.directory / "labmate.fap").write_bytes(b"tampered")
        self.assert_refused("SHA256 mismatch")

    def test_explicit_other_source_or_ci_run_refused(self):
        self.assert_refused("LabMate commit", source="1" * 40)
        self.assert_refused("Actions run", run=RUN + 1)

    def test_forged_firmware_source_refused(self):
        path = self.directory / "PROVENANCE.txt"
        path.write_text(path.read_text().replace(PIN, "1" * 40))
        self.assert_refused("Momentum base")

    def test_unexpected_or_missing_file_refused(self):
        (self.directory / "unexpected.bin").write_bytes(b"extra")
        self.assert_refused("missing/extra")
        (self.directory / "unexpected.bin").unlink()
        (self.directory / "js_gpio.module").unlink()
        self.assert_refused("missing/extra")

    def test_symlink_refused(self):
        path = self.directory / "labmate.fap"
        path.unlink()
        path.symlink_to(self.directory / "firmware.dfu")
        self.assert_refused("unsafe/non-regular")

    def test_corrupt_manifest_even_if_checksums_recalculated(self):
        (self.directory / "firmware-full-update.tgz").write_bytes(tgz(b"OTHER-DFU", RADIO))
        checksum(self.directory)
        self.assert_refused("embedded DFU differs")

    def test_unknown_radio_even_if_checksums_match(self):
        self.assert_refused("embedded radio differs", radio=b"trusted-different-binary")

    def test_unreadable_wrong_archive_even_if_checksums_match(self):
        (self.directory / "firmware-full-update.tgz").write_bytes(b"not-a-tar")
        checksum(self.directory)
        with self.assertRaises(tarfile.TarError):
            self.checked()

    def test_duplicate_provenance_field_refused(self):
        path = self.directory / "PROVENANCE.txt"
        path.write_text(path.read_text() + f"Actions run: {RUN}\n")
        self.assert_refused("duplicate")

    def test_missing_no_flash_warning_refused(self):
        path = self.directory / "READ_ME_FIRST.txt"
        path.write_text(path.read_text().replace("DO NOT FLASH", "SAFE TO FLASH"))
        self.assert_refused("safety warning")

    def test_duplicate_checksum_refused(self):
        path = self.directory / "SHA256SUMS.txt"
        path.write_text(path.read_text() + sha(b"x") + "  labmate.fap\n")
        self.assert_refused("duplicate")

    def test_wrong_radio_in_archive_path_refused(self):
        path = self.directory / "firmware-full-update.tgz"
        path.write_bytes(archive({"f7-update-test/radio.bin": RADIO}))
        checksum(self.directory)
        self.assert_refused("missing radio, SD resources")

    def test_missing_radio_refused(self):
        path = self.directory / "firmware-full-update.tgz"
        path.write_bytes(archive({"f7-update-test/firmware.dfu": b"TEST-DFU"}))
        checksum(self.directory)
        self.assert_refused("exactly one bounded embedded radio")


if __name__ == "__main__":
    unittest.main()
