#!/usr/bin/env python3
"""Synthetic, no-device E11 non-LabMate microSD scope exposure cases."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from survey_v18_e11_external_sd_ro import survey


class FakeRead:
    def __init__(self, replies):
        self.replies = list(replies)
    def until(self, marker):
        if not self.replies:
            raise AssertionError("extra serial read")
        return self.replies.pop(0)


class Fake:
    CLI_PROMPT = ">: "
    def __init__(self, replies):
        self.read = FakeRead(replies)
        self.commands = []
    def send_and_wait_eol(self, command):
        self.commands.append(command)


class ExternalSDTopOnly(unittest.TestCase):
    def root(self):
        return b"[D] apps\r\n[D] apps_data\r\n[D] docs\r\n[F] some.txt 12b"

    def test_exact_scopes_no_sensitive_names_in_summary(self):
        fake = Fake((
            self.root(),
            b"[D] Tools\r\n[D] GPIO\r\n[F] personal.fap 222b",
            b"[D] labmate\r\n[D] js_app\r\n[D] secret_app\r\n[F] private.cfg 18b",
        ))
        result = survey(fake)
        self.assertEqual(fake.commands, [
            'storage list "/ext"\r',
            'storage list "/ext/apps"\r',
            'storage list "/ext/apps_data"\r',
        ])
        self.assertEqual(result["apps_data_OTHER_directories"], 2)
        self.assertEqual(result["apps_data_labmate_folder_present"], "YES")
        self.assertEqual(result["apps_data_top_level_files"], 1)
        self.assertEqual(result["ext_top_level_files"], 1)
        self.assertEqual(result["non_labmate_content_potentially_outside_existing_snapshot"], "YES")
        self.assertEqual(result["whole_sd_snapshot_verified"], "NO")
        self.assertEqual(result["E11_firmware_write_authorized"], "NO")
        summary = str(result)
        for secret in ("secret_app", "private.cfg", "personal.fap", "some.txt"):
            self.assertNotIn(secret, summary)

    def test_empty_non_labmate_is_only_unknown_not_full_sd_pass(self):
        fake = Fake((self.root(), b"Empty", b"[D] labmate"))
        result = survey(fake)
        self.assertEqual(result["non_labmate_content_potentially_outside_existing_snapshot"], "UNKNOWN")
        self.assertEqual(result["whole_sd_inventory_completed"], "NO")
        self.assertEqual(result["non_labmate_sd_files_backed_up"], "NO")

    def test_missing_mandatory_root_rejected(self):
        fake = Fake((b"[D] apps\r\n[D] docs", b"Empty", b"Empty"))
        with self.assertRaisesRegex(ValueError, "expected /ext"):
            survey(fake)

    def test_missing_card_fails_closed(self):
        fake = Fake((b"Storage error: card not ready", b"Empty", b"Empty"))
        with self.assertRaisesRegex(ValueError, "storage error"):
            survey(fake)

    def test_unexpected_unicode_refused(self):
        fake = Fake((self.root(), b"[D] Tools\r\n", b"[D] caf\xe9"))
        with self.assertRaises(UnicodeError):
            survey(fake)

    def test_case_collision_rejected(self):
        fake = Fake((self.root(), b"Empty", b"[D] js_app\r\n[D] JS_APP"))
        with self.assertRaisesRegex(ValueError, "collision"):
            survey(fake)

    def test_malformed_traversal_rejected(self):
        fake = Fake((self.root(), b"Empty", b"[D] ../evil"))
        with self.assertRaisesRegex(ValueError, "unsafe"):
            survey(fake)

    def test_no_serial_followup_after_malformed_response(self):
        fake = Fake((b"unknown-prefix",))
        with self.assertRaisesRegex(ValueError, "unrecognized"):
            survey(fake)
        self.assertEqual(fake.commands, ['storage list "/ext"\r'])

    def test_limit_refuses_oversized_entries(self):
        fake = Fake((self.root(), b"Empty", b"".join(
            ("[F] file_%04d.cfg 1b\r\n" % i).encode() for i in range(4097)
        )))
        with self.assertRaisesRegex(ValueError, "large"):
            survey(fake)

    def test_runtime_command_set_guards_in_source(self):
        from survey_v18_e11_external_sd_ro import SCOPES
        self.assertEqual(SCOPES, ("/ext", "/ext/apps", "/ext/apps_data"))


if __name__ == "__main__":
    unittest.main()
