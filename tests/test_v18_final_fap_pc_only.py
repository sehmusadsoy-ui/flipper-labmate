#!/usr/bin/env python3
"""Synthetic PC-only old-actual-FAP / final review-bundle staging security regression."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("final_pc_only",ROOT/"scripts/stage_v18_final_fap_pc_only.py")
assert spec and spec.loader
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FinalFapPcOnlyTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="v18_final_app_pc_only_")
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.candidate=self.root/"old_candidate_from_artifact"
        self.backup=self.root/"actual_device_readback_backup"
        self.output=self.root/"brand_new_pc_output"
        self.candidate.mkdir()
        self.backup.mkdir()
        self.old=b"E11 old installed mock bytes"
        self.new=b"v1.8 final review FAP"
        self.expected_before=(m.OLD_SHA,m.OLD_BYTES,m.NEW_BYTES,m.EXPECTED,m.verify)
        m.OLD_SHA=hashlib.sha256(self.old).hexdigest()
        m.OLD_BYTES=len(self.old)
        m.NEW_BYTES=len(self.new)
        m.EXPECTED={key:hashlib.sha256((self.new if key=="labmate.fap"
                      else key.encode("ascii"))).hexdigest()
                    for key in m.EXPECTED}
        m.verify=lambda path,source,run: None if (
            source==m.FINAL_SOURCE and run==m.FINAL_RUN
        ) else (_ for _ in ()).throw(ValueError("incorrect pinned source/run"))
        self.addCleanup(self.restore)
        for name in m.EXPECTED:
            (self.candidate/name).write_bytes(
                self.new if name=="labmate.fap" else name.encode("ascii"))
        (self.backup/m.OLD_NAME).write_bytes(self.old)
        (self.backup/m.MARKER_NAME).write_text("READ_ONLY VERIFIED, NOT INSTALLED")
        self.report={
            "scope":"ONLY existing /ext/apps/Tools/labmate.fap copied to PC",
            "device_write":False,"firmware_flash":False,
            "live_identity_fap_md5_verified_twice":True,
            "live_native_js_and_manifest_md5_verified_twice":True,
            "installation_performed":False,"stable_release_approved":False,
            "installed_old_fap_sha256":m.OLD_SHA,
            "installed_old_fap_bytes":m.OLD_BYTES,
            "target_candidate_fap_sha256":m.EXPECTED["labmate.fap"],
        }
        self.write_report()
    def restore(self):
        m.OLD_SHA,m.OLD_BYTES,m.NEW_BYTES,m.EXPECTED,m.verify=self.expected_before
    def write_report(self):
        (self.backup/m.REPORT_NAME).write_text(json.dumps(self.report))

    def test_valid_old_pc_backup_and_new_candidate_stage_only(self):
        x=m.stage(self.candidate,self.backup,self.output)
        self.assertTrue(x["original_fap_is_preserved"])
        self.assertFalse(x["device_write"])
        self.assertFalse(x["publication_authorized"])
        self.assertEqual((self.output/m.OUTPUT_FAP).read_bytes(),self.new)
        self.assertEqual((self.backup/m.OLD_NAME).read_bytes(),self.old)
        self.assertTrue((self.output/"VERIFIED_PC_ONLY_DO_NOT_INSTALL.txt").is_file())
        self.assertFalse((self.output/"INCOMPLETE-NOT-FOR-DEVICE.txt").exists())

    def test_reject_old_backup_corruption(self):
        (self.backup/m.OLD_NAME).write_bytes(b"x"*len(self.old))
        with self.assertRaisesRegex(ValueError,"original|actual previously installed"):
            m.examine(self.candidate,self.backup,self.output)
        self.assertFalse(self.output.exists())

    def test_reject_wrong_final_fap(self):
        (self.candidate/"labmate.fap").write_bytes(b"wrong")
        with self.assertRaisesRegex(ValueError,"pinned SHA"):
            m.stage(self.candidate,self.backup,self.output)
        self.assertFalse(self.output.exists())

    def test_reject_prewrite_report_device_write_or_wrong_candidate(self):
        self.report["device_write"]=True
        self.write_report()
        with self.assertRaisesRegex(ValueError,"prewrite PC"):
            m.stage(self.candidate,self.backup,self.output)
        self.assertFalse(self.output.exists())
        self.report["device_write"]=False
        self.report["target_candidate_fap_sha256"]="0"*64
        self.write_report()
        with self.assertRaisesRegex(ValueError,"prewrite PC"):
            m.stage(self.candidate,self.backup,self.output)

    def test_reject_existing_output_no_overwrite(self):
        self.output.mkdir()
        (self.output/"KEEP.txt").write_text("kept")
        with self.assertRaisesRegex(ValueError,"output exists"):
            m.stage(self.candidate,self.backup,self.output)
        self.assertEqual((self.output/"KEEP.txt").read_text(),"kept")

    def test_reject_output_inside_backup_or_candidate(self):
        with self.assertRaisesRegex(ValueError,"would modify candidate"):
            m.stage(self.candidate,self.backup,self.candidate/"out")
        with self.assertRaisesRegex(ValueError,"would modify candidate"):
            m.stage(self.candidate,self.backup,self.backup/"out")

    def test_reject_extra_file_or_missing_marker_in_backup(self):
        (self.backup/"extra.csv").write_text("private")
        with self.assertRaisesRegex(ValueError,"missing/extra"):
            m.stage(self.candidate,self.backup,self.output)
        (self.backup/"extra.csv").unlink()
        (self.backup/m.MARKER_NAME).unlink()
        with self.assertRaisesRegex(ValueError,"missing/extra"):
            m.stage(self.candidate,self.backup,self.output)

    def test_reject_candidate_source_run_verifier_failure(self):
        m.verify=lambda *args: (_ for _ in ()).throw(ValueError("wrong git provenance"))
        with self.assertRaisesRegex(ValueError,"provenance"):
            m.stage(self.candidate,self.backup,self.output)
        self.assertFalse(self.output.exists())


if __name__=="__main__":
    unittest.main()
