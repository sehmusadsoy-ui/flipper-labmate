#!/usr/bin/env python3
"""Simulate pinned Momentum exact CLI echo then Ready and empty-stage rules, no USB."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import resume_v18_final_fap_from_empty_stage_once as m

APP=m.APP_REMOTE
JS="/ext/apps_data/js_app/plugins/js_gpio.fal"
EV="/ext/apps_data/js_app/plugins/js_event_loop.fal"
MF="/ext/Manifest"


class R:
    def __init__(self, d): self.d=d
    def until(self,mark):
        if mark==self.d.CLI_PROMPT:
            return b"firmware: mntm-dev\ncommit: d3f89dfe\n" if self.d.kind=="device_info" else b""
        if mark==self.d.CLI_EOL and self.d.kind=="stat":
            if self.d.path not in self.d.stats:
                return m.MISSING
            return f"File, size: {self.d.stats[self.d.path]}b".encode()
        if mark==self.d.CLI_EOL and self.d.kind=="write":
            return self.d.ready
        raise AssertionError("unexpected CLI framing")


class P:
    def __init__(self,d): self.d=d; self.short=False
    def write(self,chunk):
        if self.short: return len(chunk)-1
        if self.d.pending!=len(chunk):
            raise AssertionError("unannounced byte count")
        self.d.staged.extend(chunk)
        self.d.pending=0
        self.d.calls.append(("DATA",len(chunk)))
        return len(chunk)
    def flush(self): pass


class Flipper:
    CLI_PROMPT=">: "
    CLI_EOL="\r\n"
    def __init__(self):
        self.calls=[]
        self.kind=""
        self.path=""
        self.stats={APP:81532,m.STAGE:0}
        self.bytes={APP:b"old_fap",JS:b"gpio",EV:b"ev",MF:b"manifest"}
        self.staged=bytearray()
        self.pending=0
        self.ready=b"Ready"
        self.command_echo_override=None
        self.override_stage_md5=None
        self.port=P(self)
        self.read=R(self)
    def send_and_wait_eol(self,cmd):
        self.calls.append(("CMD",cmd))
        if cmd=="device_info\r":
            self.kind="device_info"
            return b""
        if cmd.startswith('storage stat "') and cmd.endswith('"\r'):
            self.kind="stat"
            self.path=cmd.split('"')[1]
            if self.path==m.STAGE: self.stats[m.STAGE]=len(self.staged) if m.STAGE in self.stats else None
            if self.stats.get(m.STAGE) is None: self.stats.pop(m.STAGE,None)
            assert self.path in (APP,m.STAGE,m.OLD_BACKUP_TARGET)
            return b""
        if cmd.startswith(f'storage write_chunk "{m.STAGE}" '):
            self.kind="write"
            self.pending=int(cmd.split()[-1].strip())
            # Real CLI shell echoes command first and native write handler
            # emits Ready on the NEXT CRLF-delimited line.
            return cmd[:-1].encode() if self.command_echo_override is None else self.command_echo_override
        raise AssertionError("forbidden command: "+cmd)
    def hash_flipper(self,path):
        self.calls.append(("MD5",path))
        if path==m.STAGE:
            return self.override_stage_md5 or hashlib.md5(self.staged).hexdigest()
        assert path in self.bytes
        return hashlib.md5(self.bytes[path]).hexdigest()


class StrictOneShot(unittest.TestCase):
    def setUp(self):
        self.d=Flipper()
        self.blob=b"review label candidate".ljust(m.NEW_SIZE,b"0")
        self.oldsha=m.NEW_FAP_SHA
        m.NEW_FAP_SHA=hashlib.sha256(self.blob).hexdigest()
        self.addCleanup(lambda: setattr(m,"NEW_FAP_SHA",self.oldsha))
        self.post={
            "E11_APP":hashlib.md5(self.d.bytes[APP]).hexdigest(),
            "E11_JS_GPIO":hashlib.md5(self.d.bytes[JS]).hexdigest(),
            "E11_NEW_MANIFEST":hashlib.md5(self.d.bytes[MF]).hexdigest(),
        }
        self.js={
            "labmate.fap":self.post["E11_APP"],
            "js_gpio.module":self.post["E11_JS_GPIO"],
            "event_loop":hashlib.md5(self.d.bytes[EV]).hexdigest(),
        }
    def data_count(self):
        return len([x for x in self.d.calls if x[0]=="DATA"])
    def test_one_shot_zero_stage_success_and_old_app_intact(self):
        result=m.resume_once(self.d,self.blob,self.post,self.js)
        self.assertEqual(result["new_v18_fap_installed"],"NO")
        self.assertEqual(result["stage_update"],"ONLY EXISTING EMPTY NONAPP SIDECAR")
        self.assertEqual(self.d.staged,self.blob)
        self.assertEqual(self.d.bytes[APP],b"old_fap")
        self.assertEqual(self.data_count(),(m.NEW_SIZE+m.BUF-1)//m.BUF)
        self.assertFalse(any("storage remove" in c[1] or "storage rename" in c[1]
                             for c in self.d.calls if c[0]=="CMD"))
        self.assertTrue(all((m.STAGE in c[1]) for c in self.d.calls
                            if c[0]=="CMD" and "write_chunk" in c[1]))
    def test_missing_stage_refused_no_write(self):
        self.d.stats.pop(m.STAGE)
        with self.assertRaisesRegex(ValueError,"NOT exactly zero"):
            m.resume_once(self.d,self.blob,self.post,self.js)
        self.assertEqual(self.data_count(),0)
    def test_partial_stage_refused_no_write(self):
        self.d.staged.extend(b"x")
        with self.assertRaisesRegex(ValueError,"NOT exactly zero"):
            m.resume_once(self.d,self.blob,self.post,self.js)
        self.assertEqual(self.data_count(),0)
    def test_bad_zero_size_md5_refused(self):
        self.d.override_stage_md5="0"*32
        with self.assertRaisesRegex(ValueError,"NOT empty by device MD5"):
            m.resume_once(self.d,self.blob,self.post,self.js)
        self.assertEqual(self.data_count(),0)
    def test_present_old_backup_refused(self):
        self.d.stats[m.OLD_BACKUP_TARGET]=81532
        with self.assertRaisesRegex(ValueError,"no longer absent"):
            m.resume_once(self.d,self.blob,self.post,self.js)
        self.assertEqual(self.data_count(),0)
    def test_old_app_md5_mismatch_refused(self):
        self.d.bytes[APP]=b"changed"
        with self.assertRaisesRegex(ValueError,"E11_APP|labmate.fap"):
            m.resume_once(self.d,self.blob,self.post,self.js)
        self.assertEqual(self.data_count(),0)
    def test_malformed_echo_fails_before_payload(self):
        self.d.command_echo_override=b"unknown echo"
        with self.assertRaisesRegex(ValueError,"unexpected echoed CLI command"):
            m.resume_once(self.d,self.blob,self.post,self.js)
        self.assertEqual(self.data_count(),0)

    def test_malformed_second_line_ready_fails_before_payload(self):
        self.d.ready=b"\r\n"
        with self.assertRaisesRegex(ValueError,"second-line Ready"):
            m.resume_once(self.d,self.blob,self.post,self.js)
        self.assertEqual(self.data_count(),0)
    def test_short_serial_write_is_fail_closed(self):
        self.d.port.short=True
        with self.assertRaisesRegex(ValueError,"incomplete"):
            m.resume_once(self.d,self.blob,self.post,self.js)
        self.assertEqual(self.data_count(),0)
        self.assertEqual(self.d.bytes[APP],b"old_fap")
    def test_wrong_local_candidate_rejected_before_any_serial(self):
        with self.assertRaisesRegex(ValueError,"unrecognized exact"):
            m.resume_once(self.d,b"unknown",self.post,self.js)
        self.assertEqual(self.d.calls,[])
    def test_post_chunk_stat_mismatch_refused_before_more_chunks(self):
        # Emulate an SD write that was acknowledged without the expected bytes.
        original=self.d.port.write
        def acknowledge_without_saving(data):
            self.d.pending=0
            self.d.calls.append(("DATA",len(data)))
            return len(data)
        self.d.port.write=acknowledge_without_saving
        with self.assertRaisesRegex(ValueError,"acknowledged chunk length"):
            m.resume_once(self.d,self.blob,self.post,self.js)
        self.assertEqual(self.data_count(),1)
        self.assertEqual(self.d.bytes[APP],b"old_fap")


if __name__=="__main__":
    unittest.main()
