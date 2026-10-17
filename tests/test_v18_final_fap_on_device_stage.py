#!/usr/bin/env python3
"""Synthetic tests for E11 one-file on-device staging; NO USB and NO writes."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import stage_v18_final_fap_on_device_one_file as stage

class ReadQueue:
    def __init__(self,device):
        self.device=device
    def until(self,mark):
        if mark==self.device.CLI_PROMPT:
            if self.device.last=="device_info":
                return b"firmware: mntm-dev\nfirmware.commit.hash: d3f89dfe\n"
            return b""
        if mark==self.device.CLI_EOL:
            if self.device.last=="stat":
                return self.device.stat_raw
            if self.device.last=="write":
                return b"Ready" if not self.device.malformed_ready else b"Storage error: denied"
        raise AssertionError("not a pinned read frame")

class MockPort:
    def __init__(self,device):
        self.device=device
        self.short=False
        self.flush_count=0
    def write(self,b):
        if self.short:
            return len(b)-1
        self.device.stage_data.extend(b)
        self.device.calls.append(("USB-stage-bytes",len(b)))
        return len(b)
    def flush(self):
        self.flush_count+=1

class FakeE11:
    CLI_PROMPT=">: "
    CLI_EOL="\r\n"
    def __init__(self,new):
        self.new=new
        self.stage_data=bytearray()
        self.calls=[]
        self.last=""
        self.stat_raw=b""
        self.stage_already_present=False
        self.backup_already_present=False
        self.corrupt_md5=False
        self.malformed_first_ready=False
        self.malformed_ready=False
        self.untouched={
          stage.APP_REMOTE:b"original old FAP",
          "/ext/apps_data/js_app/plugins/js_gpio.fal":b"js_gpio",
          "/ext/apps_data/js_app/plugins/js_event_loop.fal":b"event_loop",
          "/ext/Manifest":b"manifest"
        }
        self.port=MockPort(self)
        self.read=ReadQueue(self)
    def send_and_wait_eol(self,cmd):
        self.calls.append(("CMD",cmd))
        if cmd=="device_info\r":
            self.last="device_info"
            return b""
        if cmd.startswith('storage stat "') and cmd.endswith('"\r'):
            self.last="stat"
            target=cmd[len('storage stat "'): -2]
            if target==stage.APP_REMOTE:
                self.stat_raw=b"File, size: 81532b"
            elif target==stage.STAGE:
                self.stat_raw=(f"File, size: {len(self.stage_data)}b".encode()
                   if self.stage_data or self.stage_already_present else stage.MISSING)
            elif target==stage.OLD_BACKUP_TARGET:
                self.stat_raw=b"File, size: 81532b" if self.backup_already_present else stage.MISSING
            else:
                raise AssertionError("unrecognized stat path")
            return b""
        if cmd.startswith(f'storage write_chunk "{stage.STAGE}" '):
            self.last="write"
            if self.stage_already_present:
                raise AssertionError("cannot write into preexisting stage")
            # CLI shell echoes command and terminates CRLF, BEFORE native
            # write_chunk prints Ready on a second CRLF-delimited line.
            return b"not-our-command" if self.malformed_first_ready else cmd[:-1].encode("ascii")
        raise AssertionError("FORBIDDEN command: "+cmd)
    def hash_flipper(self,path):
        self.calls.append(("MD5",path))
        if path==stage.STAGE:
            return "0"*32 if self.corrupt_md5 else hashlib.md5(bytes(self.stage_data)).hexdigest()
        if path not in self.untouched:
            raise AssertionError("foreign device path")
        return hashlib.md5(self.untouched[path]).hexdigest()

class StageOnlyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.backup=self.root/"saved_backup"
        self.original=self.root/"old_original_bundle"
        self.backup.mkdir()
        self.original.mkdir()
        self.new=self.root/"downloaded_final.fap"
        self.blob=b"new FAP simulation for pure host safety".ljust(stage.NEW_SIZE,b"X")
        self.new.write_bytes(self.blob)
        self.saved_sha=stage.NEW_FAP_SHA
        stage.NEW_FAP_SHA=hashlib.sha256(self.blob).hexdigest()
        self.addCleanup(lambda: setattr(stage,"NEW_FAP_SHA",self.saved_sha))
        self.existing=FakeE11(self.blob)
        self.post={
            "E11_APP":hashlib.md5(self.existing.untouched[stage.APP_REMOTE]).hexdigest(),
            "E11_JS_GPIO":hashlib.md5(self.existing.untouched["/ext/apps_data/js_app/plugins/js_gpio.fal"]).hexdigest(),
            "E11_NEW_MANIFEST":hashlib.md5(self.existing.untouched["/ext/Manifest"]).hexdigest(),
        }
        self.js={
            "labmate.fap":self.post["E11_APP"],
            "js_gpio.module":self.post["E11_JS_GPIO"],
            "event_loop":hashlib.md5(self.existing.untouched["/ext/apps_data/js_app/plugins/js_event_loop.fal"]).hexdigest(),
        }

    def test_creates_only_one_nonapp_staged_file_old_app_intact(self):
        d=self.existing
        r=stage.stage_one_file(d,self.blob,self.post,self.js)
        self.assertEqual(bytes(d.stage_data),self.blob)
        self.assertEqual(r["new_stage_is_active_app"],"NO")
        self.assertEqual(r["old_active_app_still_installed"],"YES")
        self.assertEqual(d.untouched[stage.APP_REMOTE],b"original old FAP")
        writes=[x for x in d.calls if x[0]=="CMD" and "write_chunk" in x[1]]
        self.assertEqual(len(writes),(stage.NEW_SIZE+stage.BUF-1)//stage.BUF)
        self.assertTrue(all(stage.STAGE in x[1] and stage.APP_REMOTE not in x[1] for x in writes))
        self.assertFalse(any("remove" in x[1] or "rename" in x[1] for x in d.calls if x[0]=="CMD"))

    def test_refuse_preexisting_stage_no_write(self):
        self.existing.stage_already_present=True
        with self.assertRaisesRegex(ValueError,"already exists"):
            stage.stage_one_file(self.existing,self.blob,self.post,self.js)
        self.assertFalse(any(x[0]=="USB-stage-bytes" for x in self.existing.calls))

    def test_refuse_preexisting_old_backup_path(self):
        self.existing.backup_already_present=True
        with self.assertRaisesRegex(ValueError,"already exists"):
            stage.stage_one_file(self.existing,self.blob,self.post,self.js)
        self.assertEqual(len(self.existing.stage_data),0)

    def test_refuse_firmware_identity_change(self):
        self.existing.read.until=lambda mark: b"firmware: unknown" if mark==self.existing.CLI_PROMPT else b""
        with self.assertRaisesRegex(ValueError,"firmware"):
            stage.stage_one_file(self.existing,self.blob,self.post,self.js)
        self.assertEqual(len(self.existing.stage_data),0)

    def test_refuse_live_old_app_mismatch(self):
        self.existing.untouched[stage.APP_REMOTE]=b"some other fap"
        with self.assertRaisesRegex(ValueError,"E11_APP"):
            stage.stage_one_file(self.existing,self.blob,self.post,self.js)
        self.assertEqual(len(self.existing.stage_data),0)

    def test_refuse_short_serial_write_and_leave_original(self):
        self.existing.port.short=True
        with self.assertRaisesRegex(ValueError,"incomplete"):
            stage.stage_one_file(self.existing,self.blob,self.post,self.js)
        self.assertEqual(self.existing.untouched[stage.APP_REMOTE],b"original old FAP")

    def test_real_momentum_echo_first_then_ready_second(self):
        result=stage.stage_one_file(self.existing,self.blob,self.post,self.js)
        self.assertEqual(result["final_swap_performed"],"NO")
        self.assertEqual(bytes(self.existing.stage_data),self.blob)
        self.assertTrue(all(stage.STAGE in x[1]
                            for x in self.existing.calls if x[0]=="CMD" and "write_chunk" in x[1]))

    def test_refuse_wrong_echo_before_any_binary_send(self):
        self.existing.malformed_first_ready=True
        with self.assertRaisesRegex(ValueError,"unexpected echoed CLI command"):
            stage.stage_one_file(self.existing,self.blob,self.post,self.js)
        self.assertEqual(len(self.existing.stage_data),0)
        self.assertFalse(any(x[0]=="USB-stage-bytes" for x in self.existing.calls))

    def test_refuse_wrong_second_ready_before_any_binary_send(self):
        self.existing.malformed_ready=True
        with self.assertRaisesRegex(ValueError,"second-line Ready"):
            stage.stage_one_file(self.existing,self.blob,self.post,self.js)
        self.assertEqual(len(self.existing.stage_data),0)
        self.assertFalse(any(x[0]=="USB-stage-bytes" for x in self.existing.calls))

    def test_refuse_stage_wrong_device_md5(self):
        self.existing.corrupt_md5=True
        with self.assertRaisesRegex(ValueError,"MD5 mismatch"):
            stage.stage_one_file(self.existing,self.blob,self.post,self.js)
        self.assertEqual(self.existing.untouched[stage.APP_REMOTE],b"original old FAP")

    def test_refuse_unknown_candidate_bytes_no_storage_command(self):
        with self.assertRaisesRegex(ValueError,"unknown target"):
            stage.stage_one_file(self.existing,b"bad",self.post,self.js)
        self.assertEqual(self.existing.calls,[])

    def test_pc_backup_acceptance_is_required_before_device(self):
        from unittest.mock import patch
        source=stage
        old=source.EXPECTED_SHA
        oldlen=source.EXPECTED_BYTES
        source.EXPECTED_SHA=hashlib.sha256(b"saved old").hexdigest()
        source.EXPECTED_BYTES=len(b"saved old")
        try:
            (self.backup/source.BACKUP_NAME).write_bytes(b"saved old")
            (self.backup/source.MARKER).write_text("verified")
            meta={
              "scope":"ONLY existing /ext/apps/Tools/labmate.fap copied to PC",
              "device_write":False,"firmware_flash":False,
              "target_candidate_fap_sha256":source.NEW_FAP_SHA,
              "installed_old_fap_sha256":source.EXPECTED_SHA,
              "installed_old_fap_bytes":source.EXPECTED_BYTES,
              "live_identity_fap_md5_verified_twice":True,
              "live_native_js_and_manifest_md5_verified_twice":True,
              "installation_performed":False,"stable_release_approved":False,
            }
            (self.backup/source.REPORT).write_text(json.dumps(meta))
            self.assertEqual(source.local_preflight(self.new,self.backup,self.original),self.blob)
            meta["device_write"]=True
            (self.backup/source.REPORT).write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError,"prewrite report"):
                source.local_preflight(self.new,self.backup,self.original)
        finally:
            source.EXPECTED_SHA=old
            source.EXPECTED_BYTES=oldlen

if __name__=="__main__":
    unittest.main()
