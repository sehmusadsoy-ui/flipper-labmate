#!/usr/bin/env python3
"""Host-only fail-closed H0 stage probe, exact marker order and integrity tests."""
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import check_v18_e11_h0_stage_v3 as h


def reply(*stages,done=True,error=False,busy=False):
    bits=[b"Running script /hidden/path, press CTRL+C to stop\r\n"]
    for key,marker in h.STAGES:
        if key in stages: bits.append(marker+b"\r\n")
    if error: bits.append(b"---- ERROR ----\r\nOTHER UNKNOWN ERROR\r\nTrace:\r\n/private\r\n")
    if busy: bits.append(b"GPIO pin BUSY\r\n")
    if done: bits.append(b"Script done!\r\n")
    return b"".join(bits)


class StageV3Tests(unittest.TestCase):
    def test_exact_lf_source_byte_digest_and_readonly_ops(self):
        self.assertEqual(h.REMOTE_PROBE,"/ext/apps/Scripts/e11_h0_stage_v3.js")
        self.assertEqual(h.PINNED_PROBE_SHA256,"295312109620552b1669533ec644f4fe9f7d150055d5859883e38ddcd849f190")
        self.assertEqual(hashlib.sha256(h.LOCAL_PROBE.read_bytes()).hexdigest(),h.PINNED_PROBE_SHA256)
        self.assertEqual(len(h.prove_local_script()),32)
        code=h.LOCAL_PROBE.read_text("ascii")
        executable=[line.strip() for line in code.splitlines() if line.strip() and not line.startswith("//")]
        self.assertEqual(executable,[
            'print("E11_H3_BEGIN");',
            'let eventLoop = require("event_loop");',
            'print("E11_H3_EVENT_LOOP_OK");',
            'let gpio = require("gpio");',
            'print("E11_H3_GPIO_OK");',
            'let pa7 = gpio.get("PA7");',
            'print("E11_H3_PIN_OK");',
            'let value = pa7.read();',
            'print("E11_H3_READ_OK");',
        ])
        self.assertNotIn("pwmWrite(",code)
        self.assertNotIn("gpio.init(",code)
        self.assertNotIn("pa7.init(",code)
        self.assertNotIn("pa7.write(",code)
        self.assertNotIn("pwmStop(",code)

    def test_only_all_ordered_unique_pass(self):
        names=[name for name,_ in h.STAGES]
        self.assertIn("PASS",h.evaluate_output(reply(*names)))
        bad=reply(*names)+b"---- ERROR ----\n"
        with self.assertRaises(ValueError):h.evaluate_output(bad)
        with self.assertRaises(ValueError):h.evaluate_output(reply(*names,done=False))
        with self.assertRaises(ValueError):h.evaluate_output(reply(*names,busy=True))
        with self.assertRaises(ValueError):h.evaluate_output(reply(*names, error=True))
        with self.assertRaises(ValueError):
            h.evaluate_output(b"Running script /private\n"+b"\n".join(z for _,z in reversed(h.STAGES))+b"\nScript done!")
        with self.assertRaises(ValueError):
            h.evaluate_output(reply(*names)+h.STAGES[2][1])

    def test_missing_stage_not_mislabeled_pass(self):
        for i in range(len(h.STAGES)):
            names=[x for j,(x,_) in enumerate(h.STAGES) if j != i]
            with self.subTest(stage=i),self.assertRaisesRegex(ValueError,"H0 v3 staged JS"):
                h.evaluate_output(reply(*names,done=False,error=True))

    def test_fixed_boolean_diagnostics_privacy(self):
        raw=reply("begin","event_loop",done=False,error=True)
        status=h.stage_status(raw)
        self.assertIn("begin=YES",status)
        self.assertIn("event_loop=YES",status)
        self.assertIn("gpio=NO",status)
        self.assertIn("trace=YES",status)
        self.assertNotIn("hidden",status)
        self.assertNotIn("private",status)
        with self.assertRaises(ValueError) as e: h.evaluate_output(raw)
        self.assertNotIn("private",str(e.exception))

    def test_explicit_matching_bundle_and_script_are_mandatory(self):
        import inspect
        source=inspect.getsource(h.run)
        for token in ("prove_local_script()", "local_expected_md5(candidate)", "compare_remote_identity(identity,remote,full)", "client.hash_flipper(REMOTE_PROBE)", "actual != probe_md5", "client.read.until(client.CLI_PROMPT)"):
            self.assertIn(token,source)
        self.assertIn('send_and_wait_eol("js "+REMOTE_PROBE+"\\r")',source)
        self.assertEqual(source.count('send_and_wait_eol("js '),1)
        for forbidden in ('"storage remove','"storage write','"storage send','"firmware update','"reset'):
            self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()
