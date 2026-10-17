#!/usr/bin/env python3
"""Mocked E11 final-label prewrite: ZERO real device, SD or user files touched."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import check_v18_e11_final_fap_prewrite_ro as pre

class MockRead:
    def __init__(self,info):
        self.info=info
    def until(self,marker):
        return self.info

class MockFlipper:
    CLI_PROMPT=">: "
    def __init__(self,app,*,tamper=False,second_change=False,short_read=False,as_bytes=False,bad_type=False):
        self.app=app
        self.read=MockRead(b"firmware: mntm-dev / commit d3f89dfe\n")
        self.first_pass={}
        self.calls=[]
        self.changed=second_change
        self.n=0
        self.tamper=tamper
        self.short_read=short_read
        self.as_bytes=as_bytes
        self.bad_type=bad_type
        for path,contents in [
            (pre.APP_REMOTE,app),
            ("/ext/apps_data/js_app/plugins/js_gpio.fal",b"js-gpio"),
            ("/ext/apps_data/js_app/plugins/js_event_loop.fal",b"event-loop"),
            ("/ext/Manifest",b"manifest"),
        ]:
            self.first_pass[path]=hashlib.md5(contents).hexdigest()
    def send_and_wait_eol(self,command):
        assert command=="device_info\r"
        self.calls.append(command)
    def hash_flipper(self,path):
        assert path in self.first_pass
        self.calls.append("storage md5: "+path)
        self.n+=1
        if self.changed and self.n>6 and path==pre.APP_REMOTE:
            return "0"*32
        return self.first_pass[path]
    def read_file(self,path):
        assert path==pre.APP_REMOTE
        self.calls.append("storage read_chunks: "+path)
        if self.bad_type:
            return "not binary"
        if self.short_read:
            return bytearray(self.app[:-1])
        if self.tamper:
            # Corrupt one byte WITHOUT changing length, so SHA must fail.
            return bytearray(b"X"+self.app[1:])
        # Actual pinned Momentum FlipperStorage.read_file() returns bytearray.
        return bytes(self.app) if self.as_bytes else bytearray(self.app)


class PrewriteTests(unittest.TestCase):
    def setUp(self):
        self.work=tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root=Path(self.work.name)
        self.old_sha=pre.EXPECTED_SHA
        self.old_bytes=pre.EXPECTED_BYTES
        self.app=b"app: safe test fixture"
        pre.EXPECTED_SHA=hashlib.sha256(self.app).hexdigest()
        pre.EXPECTED_BYTES=len(self.app)
        self.addCleanup(lambda: setattr(pre,"EXPECTED_SHA",self.old_sha))
        self.addCleanup(lambda: setattr(pre,"EXPECTED_BYTES",self.old_bytes))
        mock=MockFlipper(self.app)
        self.post={
            "E11_APP":mock.first_pass[pre.APP_REMOTE],
            "E11_JS_GPIO":mock.first_pass["/ext/apps_data/js_app/plugins/js_gpio.fal"],
            "E11_NEW_MANIFEST":mock.first_pass["/ext/Manifest"],
        }
        self.js={
            "labmate.fap":mock.first_pass[pre.APP_REMOTE],
            "js_gpio.module":mock.first_pass["/ext/apps_data/js_app/plugins/js_gpio.fal"],
            "event_loop":mock.first_pass["/ext/apps_data/js_app/plugins/js_event_loop.fal"],
        }
        self.output=self.root/"new-backup"
    def test_exact_device_identity_and_one_fap_pc_backup(self):
        mock=MockFlipper(self.app)
        result=pre.check_and_copy(mock,self.post,self.js,self.output)
        self.assertIn("PINNED E11",result["device_identity"])
        self.assertEqual((self.output/pre.BACKUP_NAME).read_bytes(),self.app)
        self.assertTrue((self.output/"READ_ONLY_PC_FAP_BACKUP_VERIFIED.txt").is_file())
        self.assertFalse((self.output/"INCOMPLETE-DO-NOT-RESTORE.txt").exists())
        self.assertEqual(sum(s.startswith("storage read_chunks") for s in mock.calls),1)
        self.assertEqual(len([s for s in mock.calls if s.startswith("storage md5")]),12)
    def test_rejects_changed_device_identity_without_creating_backup(self):
        mock=MockFlipper(self.app,second_change=True)
        with self.assertRaisesRegex(ValueError,"identity changed"):
            pre.check_and_copy(mock,self.post,self.js,self.output)
        self.assertFalse(self.output.exists())
    def test_readback_returns_real_momentum_bytearray(self):
        mock=MockFlipper(self.app)
        self.assertIsInstance(mock.read_file(pre.APP_REMOTE), bytearray)
        pre.check_and_copy(mock,self.post,self.js,self.output)
        self.assertEqual((self.output/pre.BACKUP_NAME).read_bytes(),self.app)

    def test_accepts_explicit_bytes_if_future_api_changes(self):
        mock=MockFlipper(self.app,as_bytes=True)
        pre.check_and_copy(mock,self.post,self.js,self.output)
        self.assertEqual((self.output/pre.BACKUP_NAME).read_bytes(),self.app)

    def test_rejects_short_serial_read(self):
        mock=MockFlipper(self.app,short_read=True)
        with self.assertRaisesRegex(ValueError,"incomplete/oversized"):
            pre.check_and_copy(mock,self.post,self.js,self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_same_length_corrupt_serial_read(self):
        mock=MockFlipper(self.app,tamper=True)
        with self.assertRaisesRegex(ValueError,"SHA256 differs"):
            pre.check_and_copy(mock,self.post,self.js,self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_nonbinary_return_without_creating_backup(self):
        mock=MockFlipper(self.app,bad_type=True)
        with self.assertRaisesRegex(ValueError,"nonbinary"):
            pre.check_and_copy(mock,self.post,self.js,self.output)
        self.assertFalse(self.output.exists())
    def test_rejects_wrong_firmware_before_fap_readback(self):
        mock=MockFlipper(self.app)
        mock.read=MockRead(b"firmware: mntm-012\n")
        with self.assertRaisesRegex(ValueError,"firmware"):
            pre.check_and_copy(mock,self.post,self.js,self.output)
        self.assertFalse(any(s.startswith("storage read_chunks") for s in mock.calls))
        self.assertFalse(self.output.exists())
    def test_rejects_wrong_manifest_or_plugin_before_read(self):
        mock=MockFlipper(self.app)
        bad=dict(self.post);bad["E11_NEW_MANIFEST"]="0"*32
        with self.assertRaisesRegex(ValueError,"E11_NEW_MANIFEST"):
            pre.check_and_copy(mock,bad,self.js,self.output)
        self.assertFalse(self.output.exists())
        self.assertFalse(any(s.startswith("storage read_chunks") for s in mock.calls))
    def test_refuse_existing_backup_even_if_empty(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError,"exists"):
            pre.safe_output(self.output)
    def test_refuse_missing_parent(self):
        with self.assertRaisesRegex(ValueError,"parent"):
            pre.safe_output(self.root/"missing"/"backup")
    def test_no_device_operation_if_com_port_invalid(self):
        with self.assertRaisesRegex(ValueError,"COMn"):
            pre.perform("COM0",self.root,self.root,self.output)
        self.assertFalse(self.output.exists())


if __name__=="__main__":
    unittest.main()
