#!/usr/bin/env python3
"""No USB: tests read-only CLI echo capture using pinned Momentum shell ordering."""
from __future__ import annotations

import hashlib
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import probe_e11_cli_echo_stat_ro as ro

APP=ro.APP_REMOTE
JS="/ext/apps_data/js_app/plugins/js_gpio.fal"
EV="/ext/apps_data/js_app/plugins/js_event_loop.fal"
MF="/ext/Manifest"


class Buffered:
    def __init__(self, device):
        self.device=device
    def until(self, marker):
        d=self.device
        if marker==d.CLI_EOL and d.mode=="stat":
            if d.path not in d.sizes:
                return b"Storage error: file/dir not exist"
            return f"File, size: {d.sizes[d.path]}b".encode()
        if marker==d.CLI_PROMPT:
            if d.mode=="device_info":
                return b"firmware: mntm-dev\ncommit: d3f89dfe\n"
            return b"\r\n"
        raise AssertionError("Unexpected read-only serial framing")


class FakeDevice:
    CLI_EOL="\r\n"
    CLI_PROMPT=">: "
    def __init__(self):
        self.mode=""
        self.path=""
        self.sizes={APP:81532, ro.STAGE:0}
        self.bad_first_line=False
        self.bytes={
            APP:b"pinned E11",JS:b"js gpio",EV:b"js event",MF:b"resource manifest"
        }
        self.calls=[]
        self.read=Buffered(self)
    def send_and_wait_eol(self, command):
        self.calls.append("CLI " + command.rstrip("\r"))
        if command=="device_info\r":
            self.mode="device_info"
            return b"device_info"
        if command.startswith('storage stat "') and command.endswith('"\r'):
            self.mode="stat"
            self.path=command.split('"')[1]
            assert self.path in (APP,ro.STAGE,ro.RESERVED)
            return b"unknown" if self.bad_first_line else command[:-1].encode()
        raise AssertionError("Forbidden device command: " + command)
    def hash_flipper(self, path):
        self.calls.append("MD5 " + path)
        if path==ro.STAGE:
            return ro.EMPTY_MD5 if self.sizes.get(ro.STAGE)==0 else hashlib.md5(b"nonempty").hexdigest()
        if path not in self.bytes:
            raise AssertionError("Forbidden md5 path " + path)
        return hashlib.md5(self.bytes[path]).hexdigest()


class RealEchoReadOnly(unittest.TestCase):
    def setUp(self):
        self.d=FakeDevice()
        self.post={
            "E11_APP":self.d.hash_flipper(APP),
            "E11_JS_GPIO":self.d.hash_flipper(JS),
            "E11_NEW_MANIFEST":self.d.hash_flipper(MF),
        }
        self.js={
            "labmate.fap":self.post["E11_APP"],
            "js_gpio.module":self.post["E11_JS_GPIO"],
            "event_loop":self.d.hash_flipper(EV),
        }
        self.d.calls.clear()
    def no_writes(self):
        self.assertTrue(all(c.startswith(("CLI device_info","CLI storage stat ","MD5 "))
                            for c in self.d.calls))
        self.assertFalse(any("write_chunk" in c or "remove " in c or "rename " in c
                             for c in self.d.calls))
    def test_fixed_stage_stat_echo_command_then_size(self):
        result=ro.probe_fixed_stat(self.d)
        self.assertEqual(result["cli_first_line"],"EXACT_COMMAND_ECHO")
        self.assertEqual(result["cli_second_line"],"EXPECTED_EMPTY_FILE")
        self.assertEqual(result["cli_tail"],"EXPECTED_CRLF")
        self.assertTrue(result["real_echo_ready_handshake_confirmed"].startswith("NO"))
        self.no_writes()
    def test_full_readonly_audit_keeps_old_and_empty(self):
        result=ro.read_only_audit(self.d,self.post,self.js)
        self.assertEqual(result["real_cli_echo"],"EXACT_COMMAND_ECHO")
        self.assertEqual(result["writing"],"NONE")
        self.assertEqual(result["fap_installed"],"NO")
        self.assertEqual(result["existing_stage"],"PRESENT EMPTY 0 BYTES, MD5 MATCH")
        self.no_writes()
    def test_echo_mismatch_fails_without_any_upload(self):
        self.d.bad_first_line=True
        with self.assertRaisesRegex(ValueError,"framing unexpected"):
            ro.read_only_audit(self.d,self.post,self.js)
        self.no_writes()
    def test_missing_stage_fails_before_any_write(self):
        self.d.sizes.pop(ro.STAGE)
        with self.assertRaisesRegex(ValueError,"framing unexpected"):
            ro.read_only_audit(self.d,self.post,self.js)
        self.no_writes()
    def test_nonempty_sidecar_fails(self):
        self.d.sizes[ro.STAGE]=3
        with self.assertRaisesRegex(ValueError,"framing unexpected"):
            ro.read_only_audit(self.d,self.post,self.js)
        self.no_writes()
    def test_reserved_backup_path_exists_stops(self):
        self.d.sizes[ro.RESERVED]=81532
        with self.assertRaisesRegex(ValueError,"reserved backup path"):
            ro.read_only_audit(self.d,self.post,self.js)
        self.no_writes()
    def test_old_active_app_mismatch_stops(self):
        self.d.bytes[APP]=b"modified"
        with self.assertRaisesRegex(ValueError,"E11_APP|labmate.fap"):
            ro.read_only_audit(self.d,self.post,self.js)
        self.no_writes()
    def test_malformed_resource_stop(self):
        self.d.bytes[MF]=b"some other manifest"
        with self.assertRaisesRegex(ValueError,"E11_NEW_MANIFEST"):
            ro.read_only_audit(self.d,self.post,self.js)
        self.no_writes()
    def test_strictly_allowlisted_stat_only(self):
        with self.assertRaisesRegex(ValueError,"unapproved stage stat"):
            ro.stat_exact(self.d,"/ext/apps_data/labmate/record.csv")
        self.assertEqual(self.d.calls,[])


if __name__ == "__main__":
    unittest.main()
