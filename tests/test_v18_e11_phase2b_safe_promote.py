#!/usr/bin/env python3
"""HOST ONLY: safe two-rename E11 phase2B simulated Momentum CLI; never USB."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import prepare_v18_e11_phase2b_safe_promote as m

JS="/ext/apps_data/js_app/plugins/js_gpio.fal"
EV="/ext/apps_data/js_app/plugins/js_event_loop.fal"
MF="/ext/Manifest"


class Reader:
    def __init__(self,device): self.device=device
    def until(self,delimiter):
        d=self.device
        if delimiter==d.CLI_EOL and d.kind=="stat":
            return d.stat_value
        if delimiter==d.CLI_PROMPT:
            if d.kind=="device_info":
                return b"firmware: mntm-dev\nfirmware.commit.hash: d3f89dfe\n"
            if d.kind=="stat":
                return b"\r\n"
            if d.kind=="rename":
                if d.raise_timeout:
                    raise TimeoutError("simulated disconnect")
                return b"Storage error: denied\r\n\r\n" if d.rename_reply_error else b"\r\n"
        raise AssertionError("Unexpected mocked serial framing "+str(delimiter))


class FakeNative:
    CLI_EOL="\r\n"
    CLI_PROMPT=">: "
    def __init__(self):
        self.storage={
            m.APP_REMOTE:b"O"*81532,
            m.STAGE:b"N"*81528,
            JS:b"G"*122,
            EV:b"E"*122,
            MF:b"M"*122
        }
        self.calls=[]
        self.kind=""
        self.stat_value=b""
        self.rename_count=0
        self.mutate_on_rename=True
        self.second_rename_fails=False
        self.rename_reply_error=False
        self.echo_wrong=False
        self.raise_timeout=False
        self.read=Reader(self)
    def send_and_wait_eol(self,cmd):
        self.calls.append(("CMD",cmd))
        if cmd=="device_info\r":
            self.kind="device_info"
            return b"device_info"
        if cmd.startswith('storage stat "') and cmd.endswith('"\r'):
            self.kind="stat"
            p=cmd.split('"')[1]
            if p not in m.ALLOW:
                raise AssertionError("unapproved stat")
            self.stat_value=(f"File, size: {len(self.storage[p])}b".encode()
                             if p in self.storage else m.ABSENT)
            return cmd[:-1].encode()
        if cmd.startswith('storage rename "') and cmd.endswith('"\r'):
            self.kind="rename"
            parts=cmd.split('"')
            src,dst=parts[1],parts[3]
            self.rename_count+=1
            if (src,dst) not in {(m.APP_REMOTE,m.BACKUP),(m.STAGE,m.APP_REMOTE)}:
                raise AssertionError("unexpected rename targets")
            if not self.mutate_on_rename or (self.second_rename_fails and self.rename_count==2):
                return b"mismatched native echo"
            if src not in self.storage or dst in self.storage:
                raise AssertionError("non-safe rename attempted")
            self.storage[dst]=self.storage.pop(src)
            return b"mismatched native echo" if self.echo_wrong else cmd[:-1].encode()
        raise AssertionError("FORBIDDEN device CLI command: "+cmd)
    def hash_flipper(self,p):
        self.calls.append(("MD5",p))
        if p not in self.storage:
            raise AssertionError("MD5 of nonexistent file "+p)
        return hashlib.md5(self.storage[p]).hexdigest()


class TwoRenameHostTests(unittest.TestCase):
    def setUp(self):
        self.d=FakeNative()
        self.old=b"O"*81532
        self.new=b"N"*81528
        self.oldmd5=hashlib.md5(self.old).hexdigest()
        self.newmd5=hashlib.md5(self.new).hexdigest()
        self.post={
            "E11_APP":self.oldmd5,
            "E11_JS_GPIO":hashlib.md5(self.d.storage[JS]).hexdigest(),
            "E11_NEW_MANIFEST":hashlib.md5(self.d.storage[MF]).hexdigest()
        }
        self.js={
            "labmate.fap":self.oldmd5,
            "js_gpio.module":self.post["E11_JS_GPIO"],
            "event_loop":hashlib.md5(self.d.storage[EV]).hexdigest()
        }
    def assertSafeCommands(self):
        for kind,value in self.d.calls:
            if kind=="MD5":
                self.assertIn(value,set(m.ALLOW)|{JS,EV,MF})
            elif kind=="CMD":
                self.assertTrue(value=="device_info\r" or
                                value.startswith("storage stat ") or
                                value.startswith("storage rename "))
            else:
                self.fail("unknown native action")
        self.assertFalse(any("storage write_chunk " in item[1] or
                             "storage remove " in item[1] or
                             "storage copy " in item[1] or
                             "firmware " in item[1]
                             for item in self.d.calls if item[0]=="CMD"))
    def test_two_safe_renames_verified_full_phase2b_file_id(self):
        result=m.promote_two_renames(self.d,self.post,self.js,self.oldmd5,self.newmd5)
        self.assertEqual(result["stage_now_absent"],"YES")
        self.assertEqual(result["new_v18_app_boot_test"],"PENDING")
        self.assertEqual(self.d.rename_count,2)
        self.assertEqual(self.d.storage[m.APP_REMOTE],self.new)
        self.assertEqual(self.d.storage[m.BACKUP],self.old)
        self.assertNotIn(m.STAGE,self.d.storage)
        self.assertSafeCommands()
    def test_wrong_old_fap_size_refuse_before_first_rename(self):
        self.d.storage[m.APP_REMOTE]=b"tampered"
        with self.assertRaises(ValueError):m.promote_two_renames(self.d,self.post,self.js,self.oldmd5,self.newmd5)
        self.assertEqual(self.d.rename_count,0)
        self.assertSafeCommands()
    def test_stage_md5_tamper_refuse_before_first_rename(self):
        self.d.storage[m.STAGE]=b"x"*81528
        with self.assertRaisesRegex(ValueError,"staged|MD5"):m.promote_two_renames(self.d,self.post,self.js,self.oldmd5,self.newmd5)
        self.assertEqual(self.d.rename_count,0)
        self.assertSafeCommands()
    def test_existing_reserved_backup_refuse_before_first_rename(self):
        self.d.storage[m.BACKUP]=b"Q"*81532
        with self.assertRaisesRegex(ValueError,"backup path"):m.promote_two_renames(self.d,self.post,self.js,self.oldmd5,self.newmd5)
        self.assertEqual(self.d.rename_count,0)
        self.assertSafeCommands()
    def test_malformed_existing_backup_size_fail_closed(self):
        self.d.storage[m.BACKUP]=b"unknown backup"
        with self.assertRaisesRegex(ValueError,"unrecognized size"):
            m.promote_two_renames(self.d,self.post,self.js,self.oldmd5,self.newmd5)
        self.assertEqual(self.d.rename_count,0)
        self.assertSafeCommands()

    def test_native_manifest_tamper_refuse_before_first_rename(self):
        self.d.storage[MF]=b"tampered manifest"
        with self.assertRaises(ValueError):m.promote_two_renames(self.d,self.post,self.js,self.oldmd5,self.newmd5)
        self.assertEqual(self.d.rename_count,0)
        self.assertSafeCommands()
    def test_bad_echo_after_first_rename_prevents_second_rename(self):
        self.d.echo_wrong=True
        with self.assertRaisesRegex(ValueError,"echo mismatch"):m.promote_two_renames(self.d,self.post,self.js,self.oldmd5,self.newmd5)
        self.assertEqual(self.d.rename_count,1)
        self.assertNotIn(m.APP_REMOTE,self.d.storage)
        self.assertEqual(self.d.storage[m.BACKUP],self.old)
        self.assertEqual(self.d.storage[m.STAGE],self.new)
        self.assertSafeCommands()
    def test_second_rename_refused_leaves_old_backup_and_stage_intact(self):
        self.d.second_rename_fails=True
        with self.assertRaisesRegex(ValueError,"echo mismatch"):m.promote_two_renames(self.d,self.post,self.js,self.oldmd5,self.newmd5)
        self.assertEqual(self.d.rename_count,2)
        self.assertNotIn(m.APP_REMOTE,self.d.storage)
        self.assertEqual(self.d.storage[m.BACKUP],self.old)
        self.assertEqual(self.d.storage[m.STAGE],self.new)
        self.assertSafeCommands()
    def test_reply_error_on_first_rename_stops_without_second(self):
        self.d.rename_reply_error=True
        with self.assertRaisesRegex(ValueError,"reply ambiguous"):m.promote_two_renames(self.d,self.post,self.js,self.oldmd5,self.newmd5)
        self.assertEqual(self.d.rename_count,1)
        self.assertEqual(self.d.storage[m.BACKUP],self.old)
        self.assertSafeCommands()
    def test_timeout_after_first_rename_stops_not_retry(self):
        self.d.raise_timeout=True
        with self.assertRaisesRegex(TimeoutError,"disconnect"):m.promote_two_renames(self.d,self.post,self.js,self.oldmd5,self.newmd5)
        self.assertEqual(self.d.rename_count,1)
        self.assertEqual(self.d.storage[m.BACKUP],self.old)
        self.assertSafeCommands()
    def test_whitelist_rejects_direct_old_file_deletion_move(self):
        with self.assertRaisesRegex(ValueError,"forbidden storage rename scope"):
            m.rename_once(self.d,m.BACKUP,m.STAGE)
        self.assertEqual(self.d.calls,[])
    def test_whitelist_rejects_unrelated_sd_stat(self):
        with self.assertRaisesRegex(ValueError,"forbidden remote stat path"):
            m.stat(self.d,"/ext/apps_data/labmate/logs/log_0051.csv")
        self.assertEqual(self.d.calls,[])


if __name__=="__main__":
    unittest.main()
