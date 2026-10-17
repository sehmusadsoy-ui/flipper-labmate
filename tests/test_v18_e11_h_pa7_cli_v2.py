#!/usr/bin/env python3
"""Host-only E11 H v2 JS prerequisite, exact identity and fail-closed CLI safety tests."""
from pathlib import Path
import hashlib
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_v18_e11_h_pa7_cli_v2 as h

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_SHA="82c2a71aac69fefe6a7e71cdce386d9c2d0a9c23074dcbc0c576e5ade4bdde5f"

class HEventLoopFirstTests(unittest.TestCase):
    def test_exact_js_checksum_and_safe_script(self):
        src=ROOT/"tests/device/e11_h_pa7_read_only_v2.js"
        self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(),EXPECTED_SHA)
        self.assertEqual(h.EXPECTED_SCRIPT_SHA256, EXPECTED_SHA)
        self.assertEqual(h.LOCAL_PROBE, src)
        self.assertEqual(h.REMOTE_PROBE,"/ext/apps/Scripts/e11_h_pa7_read_only_v2.js")
        code=src.read_text("ascii")
        ops=[line.strip() for line in code.splitlines() if line.strip() and not line.lstrip().startswith("//")]
        self.assertEqual(ops,[
            'print("E11_H_PA7_BEGIN");',
            'let eventLoop = require("event_loop");',
            'let gpio = require("gpio");',
            'let pa7 = gpio.get("PA7");',
            'let level = pa7.read();',
            'print("E11_H_PA7_READ_OK " + level);',
        ])
        self.assertLess(code.index('require("event_loop")'),code.index('require("gpio")'))
        self.assertEqual(set(h.EXPECTED_E11_SHA256),{"labmate.fap","js_gpio.module"})

    def test_free_and_busy_are_distinct(self):
        free=b"Running script test\r\nE11_H_PA7_BEGIN \r\nE11_H_PA7_READ_OK true \r\nScript done!\r\n"
        busy=b"Running script test\r\nE11_H_PA7_BEGIN\r\n---- ERROR ----\r\nGPIO pin BUSY\r\nTrace:\r\n"
        self.assertIn("FREE PASS",h.evaluate_output(free,"free").replace("JS READ WHEN FREE PASS","FREE PASS"))
        self.assertIn("BUSY DENIAL PASS",h.evaluate_output(busy,"busy"))
        for raw, mode in ((free,"busy"),(busy,"free")):
            with self.assertRaises(ValueError):h.evaluate_output(raw,mode)

    def test_fail_closed_on_non_gpio_js_error(self):
        other=b"Running script test\r\nE11_H_PA7_BEGIN\r\n---- ERROR ----\r\nmodule load fail\r\nTrace:\r\n"
        with self.assertRaisesRegex(ValueError,"gpio_busy=NO") as err:
            h.evaluate_output(other,"free")
        self.assertNotIn("module load fail",str(err.exception))
        with self.assertRaises(ValueError): h.evaluate_output(other,"busy")

    def test_refuse_wrong_installed_script_or_firmware(self):
        dev=b"mntm-dev\nfirmware.commit: d3f89dfe\n"
        hashes={"labmate.fap":"a"*32,"js_gpio.module":"b"*32,"probe":"c"*32}
        h.preflight_device(dev,hashes,hashes)
        with self.assertRaises(ValueError):
            h.preflight_device(dev,dict(hashes,probe="0"*32),hashes)
        with self.assertRaises(ValueError):
            h.preflight_device(b"mntm-012",hashes,hashes)

if __name__ == "__main__":
    unittest.main()
