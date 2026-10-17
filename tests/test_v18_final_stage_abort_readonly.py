#!/usr/bin/env python3
"""No-serial mocks for failed E11 write_chunk handshake read-only evidence."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import check_v18_final_stage_after_abort_ro as ro

APP=ro.APP_REMOTE
JS="/ext/apps_data/js_app/plugins/js_gpio.fal"
EV="/ext/apps_data/js_app/plugins/js_event_loop.fal"
MF="/ext/Manifest"


class FakeReader:
    def __init__(self, parent):
        self.parent=parent
    def until(self, marker):
        if marker==self.parent.CLI_PROMPT:
            if self.parent.kind=="device_info":
                return b"firmware: mntm-dev\ncommit: d3f89dfe\n"
            return b""
        if marker==self.parent.CLI_EOL and self.parent.kind=="stat":
            p=self.parent.last_path
            if p not in self.parent.stats:
                return ro.MISSING
            return ("File, size: "+str(self.parent.stats[p])+"b").encode()
        raise AssertionError("unexpected mock delimiter")


class Fake:
    CLI_PROMPT=">: "
    CLI_EOL="\r\n"
    def __init__(self, stage_size=None, old_size=81532, backup_size=None):
        self.kind=""
        self.last_path=None
        self.calls=[]
        self.stats={APP:old_size}
        if stage_size is not None:
            self.stats[ro.STAGE]=stage_size
        if backup_size is not None:
            self.stats[ro.BACKUP]=backup_size
        self.bytes={
            APP:b"old", JS:b"JS",EV:b"EV",MF:b"manifest"
        }
        self.read=FakeReader(self)
        self.tamper_old=False
    def send_and_wait_eol(self, command):
        self.calls.append(command)
        if command=="device_info\r":
            self.kind="device_info"
            return b""
        if command.startswith('storage stat "') and command.endswith('"\r'):
            self.kind="stat"
            self.last_path=command.split('"')[1]
            assert self.last_path in {APP,ro.STAGE,ro.BACKUP}
            return b""
        raise AssertionError("FORBIDDEN COMMAND: "+command)
    def hash_flipper(self, path):
        self.calls.append('storage md5 "'+path+'"')
        if path==ro.STAGE:
            assert ro.STAGE in self.stats
            return hashlib.md5(b"stage").hexdigest()
        assert path in self.bytes
        return ("0"*32) if (path==APP and self.tamper_old) else hashlib.md5(self.bytes[path]).hexdigest()


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        f=Fake()
        self.post={
            "E11_APP":f.hash_flipper(APP),
            "E11_JS_GPIO":f.hash_flipper(JS),
            "E11_NEW_MANIFEST":f.hash_flipper(MF),
        }
        self.js={"labmate.fap":self.post["E11_APP"],
                 "js_gpio.module":self.post["E11_JS_GPIO"],
                 "event_loop":f.hash_flipper(EV)}
    def assertNoWrites(self, f):
        self.assertTrue(all(c=="device_info\r" or
                            c.startswith("storage stat ") or c.startswith("storage md5 ")
                            for c in f.calls))
    def test_stage_absent_old_unchanged(self):
        f=Fake()
        d=ro.audit(f,self.post,self.js)
        self.assertEqual(d["stage_status"],"ABSENT")
        self.assertEqual(d["active_old_fap"],"PINNED E11 SHA-BACKED MD5 + SIZE MATCH")
        self.assertEqual(d["safe_to_retry_old_stage_script"],"NO")
        self.assertNoWrites(f)
    def test_zero_length_stage_expected_if_failed_after_ready(self):
        f=Fake(stage_size=0)
        d=ro.audit(f,self.post,self.js)
        self.assertEqual(d["stage_status"],"PRESENT EMPTY 0 BYTES")
        self.assertEqual(d["stage_md5"],hashlib.md5(b"stage").hexdigest())
        self.assertNoWrites(f)
    def test_partial_stage_is_not_accepted_or_automatically_removed(self):
        f=Fake(stage_size=73)
        d=ro.audit(f,self.post,self.js)
        self.assertIn("PRESENT 73 BYTES",d["stage_status"])
        self.assertEqual(d["final_v18_fap_installed"],"NO")
        self.assertNoWrites(f)
    def test_backup_already_created_requires_stop(self):
        f=Fake(stage_size=0,backup_size=81532)
        d=ro.audit(f,self.post,self.js)
        self.assertEqual(d["reserved_backup_target"],"PRESENT — DO NOT TOUCH")
        self.assertNoWrites(f)
    def test_old_app_size_mismatch_refuses(self):
        f=Fake(old_size=0)
        with self.assertRaisesRegex(ValueError,"active old LabMate size"):
            ro.audit(f,self.post,self.js)
        self.assertNoWrites(f)
    def test_old_app_hash_mismatch_refuses(self):
        f=Fake()
        f.bytes[APP]=b"changed-old-app"
        with self.assertRaisesRegex(ValueError,"E11_APP|labmate.fap"):
            ro.audit(f,self.post,self.js)
        self.assertNoWrites(f)
    def test_refuse_unknown_sd_stat_response(self):
        f=Fake()
        f.stats[ro.STAGE]=-1
        with self.assertRaisesRegex(ValueError,"unrecognized"):
            ro.audit(f,self.post,self.js)
        self.assertNoWrites(f)
    def test_refuse_any_unapproved_stat_path_before_serial_call(self):
        f=Fake()
        with self.assertRaisesRegex(ValueError,"unapproved"):
            ro.stat_one(f,"/ext/apps_data/labmate/user_log.csv")
        self.assertEqual(f.calls,[])


if __name__=="__main__":
    unittest.main()
