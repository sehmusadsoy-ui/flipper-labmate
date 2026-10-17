#!/usr/bin/env python3
"""Host-only no-COM tests for bounded E11 native JS PA7 read/claim screen."""
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_v18_e11_h_pa7_cli import evaluate_output, safe_cli_flags, expected_md5, preflight_device, EXPECTED_SCRIPT_SHA256

class E11HLiveProbeTests(unittest.TestCase):
    def test_idle_success(self):
        self.assertIn("PASS", evaluate_output(b"E11_H_PA7_BEGIN\r\nE11_H_PA7_READ_OK true\r\n", "free"))

    def test_busy_expected(self):
        actual = b"E11_H_PA7_BEGIN\r\n---- ERROR ----\r\nGPIO pin BUSY\r\nTrace:\r\n"
        self.assertIn("BUSY DENIAL PASS", evaluate_output(actual, "busy"))
        with self.assertRaises(ValueError): evaluate_output(actual, "free")

    def test_never_accept_wrong_or_ambiguous_result(self):
        for p, expect in (
            (b"E11_H_PA7_BEGIN\nE11_H_PA7_READ_OK true", "busy"),
            (b"E11_H_PA7_BEGIN\n---- ERROR ----\nOTHER ERROR", "busy"),
            (b"Running script!\nScript done!", "free"),
            (b"E11_H_PA7_BEGIN\nGPIO pin BUSY", "busy"),
            (b"E11_H_PA7_BEGIN\n---- ERROR ----\nGPIO pin BUSY\nE11_H_PA7_READ_OK true", "busy"),
            (b"E11_H_PA7_BEGIN\n---- ERROR ----\nE11_H_PA7_READ_OK true", "free"),
        ):
            with self.subTest(expect=expect,p=p), self.assertRaises(ValueError):
                evaluate_output(p,expect)

    def test_safe_diagnostics_on_ambiguous_h0(self):
        # No raw CLI output, IDs, private paths or values may be emitted.
        raw=b"Running script /ext/private.txt\r\nE11_H_PA7_BEGIN\r\n---- ERROR ----\r\nGPIO pin BUSY\r\nTrace:\r\n"
        flags=safe_cli_flags(raw)
        self.assertIn("begin=YES", flags)
        self.assertIn("gpio_busy=YES", flags)
        self.assertIn("error=YES", flags)
        self.assertIn("done=NO", flags)
        self.assertNotIn("private",flags)
        with self.assertRaisesRegex(ValueError,"gpio_busy=YES") as caught:
            evaluate_output(raw, "free")
        self.assertNotIn("private",str(caught.exception))

    def test_missing_print_marker_diagnostics(self):
        raw=b"Running script /ext/hidden.js\r\nScript done!\r\n"
        with self.assertRaisesRegex(ValueError,"begin=NO") as caught:
            evaluate_output(raw, "free")
        self.assertNotIn("hidden",str(caught.exception))

    def test_attestation_requires_all_matching_remote_md5(self):
        hashes={"labmate.fap":"a"*32,"js_gpio.module":"b"*32,"probe":"c"*32}
        info=b"name: mntm-dev\ncommit: d3f89dfe\n"
        preflight_device(info,hashes,hashes)
        with self.assertRaises(ValueError): preflight_device(info,{**hashes,"probe":"d"*32},hashes)
        with self.assertRaises(ValueError): preflight_device(b"name: mntm-012\n",hashes,hashes)
        with self.assertRaises(ValueError): preflight_device(info,{"labmate.fap":"a"*32},hashes)

    def test_script_byte_contract_and_exact_e11_pair(self):
        src=Path(__file__).resolve().parent / "device" / "e11_h_pa7_read_only.js"
        import hashlib
        self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(),EXPECTED_SCRIPT_SHA256)
        code=src.read_text("ascii")
        lines=[l.strip() for l in code.splitlines() if l.strip() and not l.strip().startswith("//")]
        self.assertEqual(lines, [
            'print("E11_H_PA7_BEGIN");',
            'let gpio = require("gpio");',
            'let pa7 = gpio.get("PA7");',
            'let level = pa7.read();',
            'print("E11_H_PA7_READ_OK " + level);',
        ])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): expected_md5(src,Path(tmp))

if __name__=="__main__":
    unittest.main()
