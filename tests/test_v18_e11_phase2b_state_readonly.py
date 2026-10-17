#!/usr/bin/env python3
"""HOST ONLY: strict E11 file-state classification after 0/1/2 safe renames."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"scripts"))
sys.path.insert(0,str(root/"tests"))

import check_v18_e11_phase2b_state_readonly as ro
from test_v18_e11_phase2b_safe_promote import FakeNative, JS, EV, MF


class FileStateHostTests(unittest.TestCase):
    def setUp(self):
        self.d=FakeNative()
        self.old=b"O"*81532
        self.new=b"N"*81528
        self.oldmd5=hashlib.md5(self.old).hexdigest()
        self.newmd5=hashlib.md5(self.new).hexdigest()
        self.post={
           "E11_APP":self.oldmd5,
           "E11_JS_GPIO":self.d.hash_flipper(JS),
           "E11_NEW_MANIFEST":self.d.hash_flipper(MF),
        }
        self.js={
           "labmate.fap":self.oldmd5,
           "js_gpio.module":self.post["E11_JS_GPIO"],
           "event_loop":self.d.hash_flipper(EV),
        }
        self.d.calls.clear()
    def check_no_write(self):
        self.assertTrue(all(
            (k=="MD5" and v in (set(ro.ALLOW)|{JS,EV,MF})) or
            (k=="CMD" and
                (v=="device_info\r" or v.startswith("storage stat ")))
            for k,v in self.d.calls))
        self.assertFalse(any(k=="CMD" and "rename" in v for k,v in self.d.calls))
    def audit(self):
        return ro.audit(self.d,self.post,self.js,self.oldmd5,self.newmd5)
    def test_before_first_rename_proves_original_old_and_full_stage(self):
        r=self.audit()
        self.assertEqual(r["state"],"BEFORE_PROMOTION")
        self.assertEqual(r["new_v18_FAP"],"STAGED_NOT_ACTIVE")
        self.assertEqual(r["old_E11_FAP_preserved"],"PC_BACKUP_AND_ACTIVE")
        self.check_no_write()
    def test_intermediate_disconnected_old_app_preserved_under_backup(self):
        self.d.storage[ro.BACKUP]=self.d.storage.pop(ro.APP_REMOTE)
        r=self.audit()
        self.assertEqual(r["state"],"BETWEEN_TWO_RENAMES")
        self.assertEqual(r["old_E11_FAP_preserved"],"PC_BACKUP_AND_DEVICE_BAK")
        self.assertEqual(r["new_v18_FAP"],"STAGED_NOT_ACTIVE")
        self.check_no_write()
    def test_after_second_rename_checks_new_fap_and_old_backup(self):
        self.d.storage[ro.BACKUP]=self.d.storage.pop(ro.APP_REMOTE)
        self.d.storage[ro.APP_REMOTE]=self.d.storage.pop(ro.STAGE)
        r=self.audit()
        self.assertEqual(r["state"],"AFTER_PROMOTION")
        self.assertEqual(r["new_v18_FAP"],"ACTIVE_MD5_AND_SIZE_PASS")
        self.check_no_write()
    def test_wrong_active_old_md5_fails_even_if_size_correct(self):
        self.d.storage[ro.APP_REMOTE]=b"Z"*81532
        with self.assertRaisesRegex(ValueError,"hash mismatch"):
            self.audit()
        self.check_no_write()
    def test_wrong_staged_new_md5_fails_even_if_size_correct(self):
        self.d.storage[ro.STAGE]=b"Z"*81528
        with self.assertRaisesRegex(ValueError,"hash mismatch"):
            self.audit()
        self.check_no_write()
    def test_missing_stage_before_first_rename_fail_closed(self):
        self.d.storage.pop(ro.STAGE)
        with self.assertRaisesRegex(ValueError,"not one of three"):
            self.audit()
        self.check_no_write()
    def test_backup_unexpected_and_app_still_old_no_uncertain_mutation(self):
        self.d.storage[ro.BACKUP]=self.old
        with self.assertRaisesRegex(ValueError,"not one of three"):
            self.audit()
        self.check_no_write()
    def test_failed_new_fap_after_rename_is_rejected(self):
        self.d.storage[ro.BACKUP]=self.d.storage.pop(ro.APP_REMOTE)
        self.d.storage[ro.APP_REMOTE]=b"Z"*81528
        self.d.storage.pop(ro.STAGE)
        with self.assertRaisesRegex(ValueError,"hash mismatch"):
            self.audit()
        self.check_no_write()
    def test_modified_firmware_resource_fails(self):
        self.d.storage[MF]=b"X"*122
        with self.assertRaisesRegex(ValueError,"hash mismatch"):
            self.audit()
        self.check_no_write()
    def test_unexpected_sd_size_fails(self):
        self.d.storage[ro.STAGE]=b"short"
        with self.assertRaisesRegex(ValueError,"file status framing"):
            self.audit()
        self.check_no_write()
    def test_unknown_stat_rejected_before_cli_call(self):
        with self.assertRaisesRegex(ValueError,"unapproved"):
            ro.stat_exact(self.d,"/ext/apps_data/labmate/preserved.csv")
        self.assertEqual(self.d.calls,[])


if __name__=="__main__":
    unittest.main()
