#!/usr/bin/env python3
"""Host-only E11 native JS event_loop FULL-bundle vs live MD5 reader safety tests."""
from pathlib import Path
import io
import sys
import tarfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import check_v18_e11_h_js_runtime_ro as h


def tar_with_files(files):
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode="w:gz") as archive:
        for name,payload in files:
            entry=tarfile.TarInfo(name)
            entry.size=len(payload)
            archive.addfile(entry,io.BytesIO(payload))
    return buf.getvalue()


class E11HJsRuntimeReadOnlyTests(unittest.TestCase):
    def test_known_correct_member(self):
        import hashlib
        archive=tar_with_files([
            ("./unrelated.txt",b"not loaded"),
            ("./apps_data/js_app/plugins/js_event_loop.fal",b"event-loop-bytes"),
        ])
        self.assertEqual(h.packaged_event_loop_md5(archive),hashlib.md5(b"event-loop-bytes").hexdigest())

    def test_refuse_missing_duplicate_invalid_bundle(self):
        missing=tar_with_files([("apps_data/js_app/plugins/js_gpio.fal",b"other")])
        duplicated=tar_with_files([
            (h.INNER_EVENT_LOOP,b"one"),
            ("./"+h.INNER_EVENT_LOOP,b"two")])
        for data in (missing,duplicated,b"bad",b""):
            with self.subTest(data=data[:15]),self.assertRaises((ValueError,tarfile.TarError)):
                h.packaged_event_loop_md5(data)

    def test_full_matches_and_fails_closed(self):
        expected={"labmate.fap":"a"*32,"js_gpio.module":"b"*32,"event_loop":"c"*32}
        info=b"firmware: mntm-dev\ncommit: d3f89dfe\n"
        h.compare_remote_identity(info,expected,expected)
        for change in ("labmate.fap","js_gpio.module","event_loop"):
            other=dict(expected,**{change:"d"*32})
            with self.subTest(change=change),self.assertRaises(ValueError):
                h.compare_remote_identity(info,other,expected)
        with self.assertRaises(ValueError):
            h.compare_remote_identity(b"mntm-012",expected,expected)
        with self.assertRaises(ValueError):
            h.compare_remote_identity(info,{"event_loop":"a"*32},expected)

    def test_artifact_sha_gate_before_device_transport(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                h.local_expected_md5(Path(tmp))
        self.assertTrue("firmware-full-update.tgz" in h.PINNED)
        self.assertEqual(h.REMOTE["event_loop"],"/ext/apps_data/js_app/plugins/js_event_loop.fal")

    def test_live_method_is_only_readonly_cli(self):
        code=(Path(__file__).resolve().parents[1]/"scripts"/"check_v18_e11_h_js_runtime_ro.py").read_text()
        self.assertIn('serial.send_and_wait_eol("device_info\\r")',code)
        self.assertIn("serial.hash_flipper(path)",code)
        self.assertNotIn('send_and_wait_eol("js ',code)
        for bad in ("storage remove","storage write","reset","firmware update","storage send"):
            self.assertNotIn('send_and_wait_eol("'+bad,code)

if __name__=="__main__":
    unittest.main()
