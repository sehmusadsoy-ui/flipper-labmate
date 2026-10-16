#!/usr/bin/env python3
"""Offline preflight regression: simulated files only, NO USB/flash."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from preflight_v18_e11_local import (
    ARTIFACTS, ROLLBACK, RUN, SOURCE, check_settings_archive, preflight
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_tgz(*, unsafe=False) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        d = tarfile.TarInfo("settings")
        d.type = tarfile.DIRTYPE
        tar.addfile(d)
        for i in range(14):
            name = "../escaped" if unsafe and i == 3 else f"settings/part_{i:02d}.dat"
            data = f"settings-data-{i}".encode("ascii")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class LocalE11Preflight(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.candidate = root / "candidate"
        self.rollback = root / "rollback"
        self.data = root / "labmate"
        for directory in (self.candidate, self.rollback, self.data):
            directory.mkdir()
        self.artifact_hashes = {}
        self.rollback_hashes = {}
        for name in ARTIFACTS:
            b = ("synthetic-" + name).encode()
            (self.candidate / name).write_bytes(b)
            self.artifact_hashes[name] = sha(b)
        for name in ROLLBACK:
            b = ("synthetic-rollback-" + name).encode()
            (self.rollback / name).write_bytes(b)
            self.rollback_hashes[name] = sha(b)
        self.installed = root / "readback.fap"
        self.installed.write_bytes(b"synthetic-old-installed")
        self.settings = root / "private.tgz"
        self.settings.write_bytes(make_tgz())
        for i in range(14):
            (self.data / f"log_{i}.csv").write_text("test,data\n1,2\n")
        self.verify = Mock()

    def checked(self):
        return preflight(
            self.candidate, self.rollback, self.installed,
            self.data, self.settings,
            artifact_hashes=self.artifact_hashes,
            rollback_hashes=self.rollback_hashes,
            installed_hash=sha(b"synthetic-old-installed"),
            settings_hash=sha(self.settings.read_bytes()),
            full_verify=self.verify,
        )

    def test_exact_read_only_input_fixture(self):
        self.assertEqual(self.checked(), 14)
        self.verify.assert_called_once_with(self.candidate, SOURCE, RUN)

    def test_reject_candidate_tamper(self):
        (self.candidate / "labmate.fap").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            self.checked()
        self.verify.assert_not_called()

    def test_reject_missing_rollback_firmware(self):
        (self.rollback / "flipper-z-f7-update-mntm-012.tgz").unlink()
        with self.assertRaisesRegex(ValueError, "missing, empty"):
            self.checked()

    def test_reject_readback_identity_drift(self):
        self.installed.write_bytes(b"different-app")
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            self.checked()

    def test_reject_missing_data_backup_file(self):
        (self.data / "log_1.csv").unlink()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.checked()

    def test_reject_symlinked_backup_file(self):
        f = self.data / "log_1.csv"
        f.unlink()
        f.symlink_to(self.data / "log_2.csv")
        with self.assertRaisesRegex(ValueError, "unsafe"):
            self.checked()

    def test_reject_tampered_settings_archive_digest(self):
        self.settings.write_bytes(b"not an archive")
        with self.assertRaises(tarfile.TarError):
            self.checked()

    def test_reject_unsafe_tar_traversal_even_with_recomputed_hash(self):
        self.settings.write_bytes(make_tgz(unsafe=True))
        with self.assertRaisesRegex(ValueError, "unsafe"):
            self.checked()

    def test_reject_extra_tar_member(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for i in range(15):
                data = b"x"
                info = tarfile.TarInfo(f"f{i}")
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            d = tarfile.TarInfo("directory")
            d.type = tarfile.DIRTYPE
            tar.addfile(d)
        self.settings.write_bytes(buf.getvalue())
        with self.assertRaisesRegex(ValueError, "structure"):
            self.checked()

    def test_refuse_incomplete_candidate_allow_list(self):
        bad = dict(self.artifact_hashes)
        bad.pop("js_gpio.module")
        with self.assertRaisesRegex(ValueError, "incomplete pinned candidate"):
            preflight(
                self.candidate, self.rollback, self.installed,
                self.data, self.settings,
                artifact_hashes=bad, full_verify=self.verify,
            )
        self.verify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
