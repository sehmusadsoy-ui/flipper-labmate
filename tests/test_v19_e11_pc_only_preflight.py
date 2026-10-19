#!/usr/bin/env python3
"""Offline PC-only v1.9 review gate: synthetic artifacts; NEVER accesses USB."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import prepare_v19_e11_pc_only as m


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class PCOnlyPreflightTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fap = b"f" * m.FAP_BYTES
        self.v18 = b"v" * 81528
        self.old = b"o" * 81532
        self.content = b"s" * 2128
        self.patches = [
            patch.object(m, "FAP_SHA", sha(self.fap)),
            patch.object(m, "V18_SHA", sha(self.v18)),
            patch.object(m, "E11_OLD_SHA", sha(self.old)),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

        self.reviews = self.root / "review"
        self.reviews.mkdir()
        self.zip_path = self.root / "review.zip"
        self.make_review()

        self.active = self.root / "v18"
        self.active.mkdir()
        (self.active / m.V18_BACKUP_FILE).write_bytes(self.v18)
        (self.active / "LIVE_V18_FAP_READBACK_REPORT.json").write_text(json.dumps({
            "on_device_fap_sha256": sha(self.v18),
            "device_state_before_and_after_read": "AFTER_PROMOTION",
            "device_writes": False, "v19_installed": False,
        }))
        (self.active / "READ_ONLY_PC_V18_FAP_BACKUP_VERIFIED.txt").write_text("PASS")

        self.old_backup = self.root / "old"
        self.old_backup.mkdir()
        (self.old_backup / m.OLD_BACKUP_FILE).write_bytes(self.old)
        (self.old_backup / "PREWRITE_READONLY_REPORT.json").write_text(json.dumps({
            "installed_old_fap_sha256": sha(self.old), "device_write": False,
        }))
        (self.old_backup / "READ_ONLY_PC_FAP_BACKUP_VERIFIED.txt").write_text("PASS")

        self.data = self.root / "data"
        self.data.mkdir()
        (self.data / "log_0001.csv").write_bytes(self.content)
        (self.data / "PC_SNAPSHOT_MANIFEST.json").write_text(json.dumps({
            "snapshot_scope": "ONLY /ext/apps_data/labmate",
            "snapshot_complete": True, "device_write": False,
            "full_microSD_backup": False,
            "files": {"log_0001.csv": {
                "size_bytes": 2128,
                "md5_device_screen": hashlib.md5(self.content).hexdigest(),
                "sha256_of_pc_readback": sha(self.content),
            }},
        }))
        (self.data / "READ_ONLY_SNAPSHOT_VERIFIED.txt").write_text("PASS")

    def make_review(self, *, bad_provenance=False, malicious=False):
        provenance = "\n".join([
            "SOURCE_SHA=" + m.SOURCE_SHA,
            "MOMENTUM_BASE=" + m.MOMENTUM_BASE,
            "PATCH_DIFF_SHA256=" + m.LOCAL_DIFF_SHA,
            "BUILD_MODE=" + ("FORGED" if bad_provenance else "LOCAL_WSL2"),
            "GITHUB_ACTIONS_RUN=NONE",
            "",
        ]).encode()
        items = {
            m.FAP: self.fap,
            "SHA256SUMS.txt": (sha(self.fap) + "  " + m.FAP + "\n").encode(),
            "PROVENANCE.txt": provenance,
            "READ_ME_FIRST.txt": b"REVIEW ONLY\n",
        }
        if malicious:
            items["../attack.txt"] = b"malicious"
        for old in self.reviews.iterdir():
            old.unlink()
        for name, data in items.items():
            if "/" not in name:
                (self.reviews / name).write_bytes(data)
        with zipfile.ZipFile(self.zip_path, "w") as archive:
            for name, data in items.items():
                archive.writestr("v19-local-review-3d66658/" + name, data)
        p = patch.object(m, "ZIP_SHA", sha(self.zip_path.read_bytes()))
        p.start()
        self.addCleanup(p.stop)

    def verify(self):
        candidate = m.verify_review(self.zip_path, self.reviews)
        count, size = m.verify_backups(self.active, self.old_backup, self.data)
        return candidate, count, size

    def test_good_pc_only_verification(self):
        self.assertEqual(self.verify(), (self.fap, 1, 2128))

    def test_refuse_zip_hash_drift(self):
        self.zip_path.write_bytes(self.zip_path.read_bytes() + b"changed")
        with self.assertRaises(ValueError):
            m.verify_review(self.zip_path, self.reviews)

    def test_refuse_local_extracted_candidate_drift(self):
        (self.reviews / m.FAP).write_bytes(b"x" * m.FAP_BYTES)
        with self.assertRaises(ValueError):
            m.verify_review(self.zip_path, self.reviews)

    def test_refuse_wrong_build_mode_provenance(self):
        self.make_review(bad_provenance=True)
        with self.assertRaises(ValueError):
            m.verify_review(self.zip_path, self.reviews)

    def test_refuse_malicious_zip_member(self):
        self.make_review(malicious=True)
        with self.assertRaises(ValueError):
            m.verify_review(self.zip_path, self.reviews)

    def test_refuse_bad_active_v18_backup(self):
        (self.active / m.V18_BACKUP_FILE).write_bytes(b"?" * 81528)
        with self.assertRaises(ValueError):
            m.verify_backups(self.active, self.old_backup, self.data)

    def test_refuse_bad_old_e11_backup(self):
        (self.old_backup / m.OLD_BACKUP_FILE).write_bytes(b"?" * 81532)
        with self.assertRaises(ValueError):
            m.verify_backups(self.active, self.old_backup, self.data)

    def test_refuse_modified_csv(self):
        (self.data / "log_0001.csv").write_bytes(b"!" * 2128)
        with self.assertRaises(ValueError):
            m.verify_backups(self.active, self.old_backup, self.data)

    def test_refuse_incomplete_snapshot(self):
        (self.data / "INCOMPLETE-DO-NOT-RESTORE.txt").write_text("NO")
        with self.assertRaises(ValueError):
            m.verify_backups(self.active, self.old_backup, self.data)

    def test_refuse_missing_snapshot_file(self):
        (self.data / "log_0001.csv").unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            m.verify_backups(self.active, self.old_backup, self.data)

    def test_pc_only_stage_then_reject_overwrite(self):
        fap, count, total = self.verify()
        dest = self.root / "new-pc-output"
        m.check_destination(dest, (self.active, self.old_backup, self.data, self.reviews, self.zip_path))
        m.stage_pc_only(dest, fap, count, total)
        self.assertEqual((dest / "labmate-v1.9DEV-E11-PC-ONLY.fap").read_bytes(), fap)
        self.assertTrue((dest / "PC_ONLY_PREPARATION_VERIFIED.txt").is_file())
        self.assertFalse((dest / "INCOMPLETE_DO_NOT_INSTALL_OR_RESTORE.txt").exists())
        self.assertFalse(json.loads((dest / "PC_PREPARATION_PROVENANCE.json").read_text())["device_write"])
        with self.assertRaises(ValueError):
            m.check_destination(dest, (self.active, self.data))

    def test_refuse_overlap_with_old_backup(self):
        dest = self.active / "nested"
        with self.assertRaises(ValueError):
            m.check_destination(dest, (self.active, self.old_backup, self.data))


if __name__ == "__main__":
    unittest.main()
