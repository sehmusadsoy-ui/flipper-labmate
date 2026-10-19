#!/usr/bin/env python3
"""v1.9 E11 prospective prewrite gate: no Flipper or COM usage.

Synthetic command/response tests, including premature/invalid state,
occupied reserved path, echo tampering, resource drift, and absent-only gate.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_v19_e11_device_prewrite_ro as gate


class FakeRead:
    def __init__(self, client):
        self.client = client
        self.results = []

    def until(self, marker):
        if not self.results:
            raise AssertionError("no queued fake serial response")
        return self.results.pop(0)


class FakeClient:
    CLI_EOL = "\r\n"
    CLI_PROMPT = ">: "

    def __init__(self, *, reply=gate.ABSENT, tail=b"\r\n", bad_echo=False):
        self.reply, self.tail, self.bad_echo = reply, tail, bad_echo
        self.read = FakeRead(self)
        self.commands = []

    def send_and_wait_eol(self, command):
        self.commands.append(command)
        self.read.results.extend([self.reply, self.tail])
        return b"WRONG" if self.bad_echo else command[:-1].encode("ascii")


class GateTest(unittest.TestCase):
    def setUp(self):
        self.good = {
            "state": "AFTER_PROMOTION",
            "new_v18_FAP": "ACTIVE_MD5_AND_SIZE_PASS",
            "old_E11_FAP_preserved": "PC_BACKUP_AND_DEVICE_BAK",
            "firmware_JS_gpio_eventloop_manifest": "PINNED_MD5_AND_LABEL_MATCH",
        }
        self.post = {"E11_APP": "pinned-old-app-md5"}
        self.js = {}
        self.current = "pinned-final-v18-md5"

    def test_two_absent_reserved_paths_and_double_identity_screen_pass(self):
        client = FakeClient()
        with patch.object(gate, "audit", return_value=self.good) as check:
            output = gate.attest_current_v18_and_free_names(
                client, self.post, self.js, self.current
            )
        self.assertEqual(output["v19_reserved_paths"], "BOTH_ABSENT_TWICE")
        self.assertEqual(output["device_writes"], "NONE")
        self.assertEqual(output["v19_installed"], "NO")
        self.assertEqual(check.call_count, 2)
        self.assertEqual(len(client.commands), 4)
        self.assertEqual({x.split('"')[1] for x in client.commands}, gate.RESERVED)
        self.assertTrue(all(x.startswith("storage stat ") for x in client.commands))

    def test_stage_existing_0_bytes_is_not_absent(self):
        with self.assertRaises(ValueError):
            gate.stat_reserved_absent(FakeClient(reply=b"File, size: 0b"), gate.PROPOSED_STAGE)

    def test_backup_existing_regular_file_is_not_absent(self):
        with self.assertRaises(ValueError):
            gate.stat_reserved_absent(FakeClient(reply=b"File, size: 81528b"), gate.PROPOSED_FINAL_V18_BACKUP)

    def test_reject_corrupted_echo(self):
        with self.assertRaises(ValueError):
            gate.stat_reserved_absent(FakeClient(bad_echo=True), gate.PROPOSED_STAGE)

    def test_reject_unexpected_cli_tail(self):
        with self.assertRaises(ValueError):
            gate.stat_reserved_absent(FakeClient(tail=b"garbage"), gate.PROPOSED_STAGE)

    def test_reject_unapproved_path_without_serial_operation(self):
        client = FakeClient()
        with self.assertRaises(ValueError):
            gate.stat_reserved_absent(client, "/ext/apps/Tools/labmate.fap")
        self.assertEqual(client.commands, [])

    def test_reject_current_v18_md5_or_size_not_confirmed(self):
        wrong = dict(self.good, new_v18_FAP="UNVERIFIED")
        client = FakeClient()
        with patch.object(gate, "audit", return_value=wrong):
            with self.assertRaises(ValueError):
                gate.attest_current_v18_and_free_names(client, self.post, self.js, self.current)
        self.assertEqual(client.commands, [])

    def test_reject_initial_state_before_v18_final_promotion(self):
        wrong = dict(self.good, state="BEFORE_PROMOTION")
        client = FakeClient()
        with patch.object(gate, "audit", return_value=wrong):
            with self.assertRaises(ValueError):
                gate.attest_current_v18_and_free_names(client, self.post, self.js, self.current)
        self.assertEqual(client.commands, [])

    def test_reject_missing_historical_device_backup(self):
        wrong = dict(self.good, old_E11_FAP_preserved="MISSING")
        client = FakeClient()
        with patch.object(gate, "audit", return_value=wrong):
            with self.assertRaises(ValueError):
                gate.attest_current_v18_and_free_names(client, self.post, self.js, self.current)
        self.assertEqual(client.commands, [])

    def test_reject_native_js_manifest_mismatch(self):
        wrong = dict(self.good, firmware_JS_gpio_eventloop_manifest="WRONG")
        client = FakeClient()
        with patch.object(gate, "audit", return_value=wrong):
            with self.assertRaises(ValueError):
                gate.attest_current_v18_and_free_names(client, self.post, self.js, self.current)
        self.assertEqual(client.commands, [])

    def test_reject_live_state_changes_after_reserved_path_reads(self):
        final = dict(self.good, firmware_JS_gpio_eventloop_manifest="CHANGED")
        client = FakeClient()
        with patch.object(gate, "audit", side_effect=[self.good, final]):
            with self.assertRaises(ValueError):
                gate.attest_current_v18_and_free_names(client, self.post, self.js, self.current)
        self.assertEqual(len(client.commands), 2)

    def test_reject_second_pass_reserved_path_occupied(self):
        class OccupiesAfterFirst(FakeClient):
            def send_and_wait_eol(self, command):
                if len(self.commands) == 2:
                    self.reply = b"File, size: 0b"
                return super().send_and_wait_eol(command)
        client = OccupiesAfterFirst()
        with patch.object(gate, "audit", return_value=self.good):
            with self.assertRaises(ValueError):
                gate.attest_current_v18_and_free_names(client, self.post, self.js, self.current)
        self.assertEqual(len(client.commands), 3)


if __name__ == "__main__":
    unittest.main()
