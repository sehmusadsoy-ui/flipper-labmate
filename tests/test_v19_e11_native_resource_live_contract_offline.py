#!/usr/bin/env python3
"""Real activation adapter regression: do NOT mock E11 native identity gate.

Only Flipper CLI is synthetic; identity_resources_ro() AND both real
activation rename guards are executed. Reproduces production dict shapes from
check_local() -> pinned_local_expectation(): post['E11_JS_GPIO'] but
js['js_gpio.module']. The original KeyError was masked by mocking this gate.
OFFLINE; no serial module/COM connection, firmware or on-device writes.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import activate_v19_e11_once_review_only as app
import review_v19_e11_activation_recovery_offline as logic
import simulate_v19_e11_storage_cli_offline as mockcli


class NativeE11Mock(mockcli.FakeCLI):
    def send_and_wait_eol(self, command: str) -> bytes:
        if command == "device_info\r":
            self.commands.append("device_info")
            self.replies.append(self.native_label)
            return b"device_info"
        return super().send_and_wait_eol(command)

    def hash_flipper(self, path: str) -> str:
        if path in self.native_files:
            return self.native_files[path]
        return super().hash_flipper(path)


class NativeResourceContractRegressionTest(unittest.TestCase):
    def setUp(self):
        self.v18 = b"final_v18_FAP_fixture" * 11
        self.v19 = b"v19_staged_FAP_fixture" * 13
        self.legacy = b"old_E11_DEV_fixture" * 9
        sha = lambda data: hashlib.sha256(data).hexdigest()
        for module in (logic, mockcli):
            for stem, data in (
                    ("V18", self.v18), ("V19", self.v19), ("LEGACY", self.legacy)):
                for suffix, value in (("SIZE", len(data)), ("SHA", sha(data))):
                    name = stem + "_" + suffix
                    if hasattr(module, name):
                        patched = patch.object(module, name, value)
                        patched.start()
                        self.addCleanup(patched.stop)
        pinned = {
            logic.ACTIVE: (len(self.v18), sha(self.v18)),
            logic.NEW: (len(self.v19), sha(self.v19)),
            logic.CURRENT_BACKUP: (len(self.v18), sha(self.v18)),
            logic.LEGACY_BACKUP: (len(self.legacy), sha(self.legacy)),
            logic.FAILED_V19_BACKUP: (len(self.v19), sha(self.v19)),
        }
        patched = patch.object(logic, "EXPECTED", pinned)
        patched.start()
        self.addCleanup(patched.stop)
        patched = patch.object(mockcli, "RENAMES", frozenset(logic.FORWARD))
        patched.start()
        self.addCleanup(patched.stop)
        # Existing independent live poststage reader is tested separately.
        # Never mock identity_resources_ro(): that's precisely the original bug.
        patched = patch.object(app, "attest_poststage",
                               return_value={"state": "STAGED_V19_NONAPP_ACTIVE_V18"})
        patched.start()
        self.addCleanup(patched.stop)

        self.gpio = hashlib.md5(b"actual-shape-js-gpio").hexdigest()
        self.loop = hashlib.md5(b"actual-shape-event-loop").hexdigest()
        self.manifest = hashlib.md5(b"actual-shape-manifest").hexdigest()
        self.post = {
            "E11_APP": hashlib.md5(self.legacy).hexdigest(),
            "E11_JS_GPIO": self.gpio,
            "E11_NEW_MANIFEST": self.manifest,
        }
        self.js = {
            "labmate.fap": self.post["E11_APP"],
            "js_gpio.module": self.gpio,
            "event_loop": self.loop,
        }

    def device(self):
        d = NativeE11Mock(self.v18, self.legacy)
        d.fs[logic.NEW] = self.v19
        d.native_label = b"Model: Flipper Zero\r\nFirmware: mntm-dev d3f89dfe\r\n"
        d.native_files = {
            "/ext/apps_data/js_app/plugins/js_gpio.fal": self.gpio,
            "/ext/apps_data/js_app/plugins/js_event_loop.fal": self.loop,
            "/ext/Manifest": self.manifest,
        }
        return d

    def activate(self, client, post=None, js=None):
        return app.activate_on_client_once(
            client, self.v19, self.v18, self.legacy,
            self.post if post is None else post,
            self.js if js is None else js,
            hashlib.md5(self.v18).hexdigest(),
        )

    def test_real_post_js_dict_shape_passes_native_gate_three_times(self):
        d = self.device()
        report = self.activate(d)
        self.assertEqual(report["v19_file_promotion"], "PASS_TWO_NONATOMIC_RENAMES")
        self.assertEqual(d.rename_count, 2)
        self.assertEqual(d.commands.count("device_info"), 3)
        self.assertEqual(d.fs[logic.ACTIVE], self.v19)
        self.assertEqual(d.fs[logic.CURRENT_BACKUP], self.v18)
        self.assertEqual(d.fs[logic.LEGACY_BACKUP], self.legacy)
        self.assertEqual(d.chunk_count, 0)

    def test_gpio_expected_key_is_in_js_not_post(self):
        self.assertIn("E11_JS_GPIO", self.post)
        self.assertNotIn("E11_JS_GPIO", self.js)
        self.assertIn("js_gpio.module", self.js)
        self.assertEqual(self.post["E11_JS_GPIO"], self.js["js_gpio.module"])
        d = self.device()
        app.identity_resources_ro(d, self.post, self.js)
        self.assertEqual(d.commands, ["device_info"])

    def test_missing_js_gpio_module_key_aborts_before_rename(self):
        d = self.device()
        js = dict(self.js)
        js.pop("js_gpio.module")
        with self.assertRaisesRegex(ValueError, "missing/malformed pinned E11 JS"):
            self.activate(d, js=js)
        self.assertEqual(d.rename_count, 0)

    def test_missing_js_event_loop_aborts_before_rename(self):
        d = self.device()
        js = dict(self.js)
        js.pop("event_loop")
        with self.assertRaisesRegex(ValueError, "missing/malformed pinned E11 JS"):
            self.activate(d, js=js)
        self.assertEqual(d.rename_count, 0)

    def test_wrong_length_js_gpio_expected_md5_aborts_before_rename(self):
        d = self.device()
        js = dict(self.js)
        js["js_gpio.module"] = self.gpio[:-1]
        with self.assertRaises(ValueError):
            self.activate(d, js=js)
        self.assertEqual(d.rename_count, 0)

    def test_missing_packed_gpio_parity_aborts_before_rename(self):
        d = self.device()
        post = dict(self.post)
        post.pop("E11_JS_GPIO")
        with self.assertRaisesRegex(ValueError, "packed JS GPIO module checksum parity drift"):
            self.activate(d, post=post)
        self.assertEqual(d.rename_count, 0)

    def test_main_checks_real_source_contract_before_serial_connection(self):
        main_source = Path(app.__file__).read_text("utf-8").split("def main() -> int:", 1)[1]
        self.assertLess(
            main_source.index("validate_local_native_expected(post, js)"),
            main_source.index("sdk.FlipperStorage("),
        )
        app.validate_local_native_expected(self.post, self.js)

    def test_js_gpio_live_md5_drift_aborts_before_rename(self):
        d = self.device()
        d.native_files["/ext/apps_data/js_app/plugins/js_gpio.fal"] = "0" * 32
        with self.assertRaisesRegex(ValueError, "native resource MD5 changed"):
            self.activate(d)
        self.assertEqual(d.rename_count, 0)

    def test_event_loop_live_md5_drift_aborts_before_rename(self):
        d = self.device()
        d.native_files["/ext/apps_data/js_app/plugins/js_event_loop.fal"] = "0" * 32
        with self.assertRaisesRegex(ValueError, "native resource MD5 changed"):
            self.activate(d)
        self.assertEqual(d.rename_count, 0)

    def test_manifest_live_md5_drift_aborts_before_rename(self):
        d = self.device()
        d.native_files["/ext/Manifest"] = "0" * 32
        with self.assertRaisesRegex(ValueError, "Manifest MD5 changed"):
            self.activate(d)
        self.assertEqual(d.rename_count, 0)

    def test_manifest_expected_key_missing_aborts_before_rename(self):
        d = self.device()
        post = dict(self.post)
        post.pop("E11_NEW_MANIFEST")
        with self.assertRaisesRegex(ValueError, "missing/malformed pinned E11 resource Manifest"):
            self.activate(d, post=post)
        self.assertEqual(d.rename_count, 0)

    def test_native_firmware_label_drift_aborts_before_rename(self):
        d = self.device()
        d.native_label = b"Firmware: other d3f89dfe\r\n"
        with self.assertRaisesRegex(ValueError, "firmware label/base drift"):
            self.activate(d)
        self.assertEqual(d.rename_count, 0)

    def test_native_firmware_base_drift_aborts_before_rename(self):
        d = self.device()
        d.native_label = b"Firmware: mntm-dev WRONGBASE\r\n"
        with self.assertRaisesRegex(ValueError, "firmware label/base drift"):
            self.activate(d)
        self.assertEqual(d.rename_count, 0)

    def test_native_path_mismatch_aborts_before_rename(self):
        d = self.device()
        with patch.dict(app.JS_REMOTE, {"js_gpio.module": "/bad/path"}):
            with self.assertRaisesRegex(ValueError, "original JS plugin paths changed"):
                self.activate(d)
        self.assertEqual(d.rename_count, 0)

    def test_native_identity_second_call_drift_stops_between_renames(self):
        d = self.device()
        original = d.send_and_wait_eol
        seen = [0]
        def change_after_first_rename(cmd):
            if cmd == "device_info\r":
                seen[0] += 1
                if seen[0] == 2:
                    d.native_label = b"Firmware: wrong\r\n"
            return original(cmd)
        with patch.object(d, "send_and_wait_eol", side_effect=change_after_first_rename):
            with self.assertRaisesRegex(ValueError, "firmware label/base drift"):
                self.activate(d)
        self.assertEqual(d.rename_count, 1)
        self.assertNotIn(logic.ACTIVE, d.fs)
        self.assertEqual(d.fs[logic.CURRENT_BACKUP], self.v18)
        self.assertEqual(d.fs[logic.NEW], self.v19)

    def test_no_automatic_retry_after_real_native_resource_failure(self):
        d = self.device()
        d.native_files["/ext/Manifest"] = "f" * 32
        with self.assertRaises(ValueError):
            self.activate(d)
        self.assertEqual(d.rename_count, 0)
        self.assertEqual(d.fs[logic.ACTIVE], self.v18)
        self.assertEqual(d.fs[logic.NEW], self.v19)
        self.assertEqual(d.chunk_count, 0)

    def test_real_identity_function_cannot_be_mocked_in_this_regression(self):
        source = Path(__file__).read_text("utf-8")
        forbidden = 'patch.object(app, ' + '"identity_resources_ro"'
        self.assertNotIn(forbidden, source)
        self.assertEqual(app.PINNED_NATIVE[
            "/ext/apps_data/js_app/plugins/js_gpio.fal"], "js_gpio.module")


if __name__ == "__main__":
    unittest.main()
