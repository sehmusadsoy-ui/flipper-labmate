#!/usr/bin/env python3
"""Synthetic tests for E11 preflash device identity screen. No USB used."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_v18_e11_live_preflash_identity import (
    screen_identity, EXPECTED_EXITFIX_SHA256, check_device
)

class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.device_info = b"hardware_model: Flipper Zero\r\nfirmware.version: mntm-dev\r\nfirmware.commit.hash: d3f89dfe\r\n"
        # Real saved EXITFIX is not in CI and must never be synthesized as an authentic file.
        # Patch the pinned SHA only for these explicit synthetic tests.
        self.pc_bytes = b"synthetic-test-not-a-real-FAP"
        self.pc_sha = hashlib.sha256(self.pc_bytes).hexdigest()
        self.md5 = hashlib.md5(self.pc_bytes).hexdigest()
        self.patch_hash = patch(
            "check_v18_e11_live_preflash_identity.EXPECTED_EXITFIX_SHA256",
            self.pc_sha
        )
        self.patch_hash.start()
        self.addCleanup(self.patch_hash.stop)

    def test_matching_firmware_and_fap(self):
        screen_identity(self.device_info, self.md5, self.pc_bytes)

    def test_firmware_mismatch(self):
        with self.assertRaisesRegex(ValueError, "unexpected Flipper firmware"):
            screen_identity(self.device_info.replace(b"mntm-dev", b"mntm-012"), self.md5, self.pc_bytes)

    def test_base_mismatch(self):
        with self.assertRaisesRegex(ValueError, "unexpected Flipper firmware"):
            screen_identity(self.device_info.replace(b"d3f89dfe", b"00000000"), self.md5, self.pc_bytes)

    def test_wrong_live_fap(self):
        with self.assertRaisesRegex(ValueError, "device EXITFIX differs"):
            screen_identity(self.device_info, "0" * 32, self.pc_bytes)

    def test_wrong_local_fap(self):
        with self.assertRaisesRegex(ValueError, "saved EXITFIX copy"):
            screen_identity(self.device_info, self.md5, b"different")

    def test_untrusted_md5_response(self):
        with self.assertRaisesRegex(ValueError, "invalid live FAP MD5"):
            screen_identity(self.device_info, "Storage error", self.pc_bytes)

    def test_invalid_info_bytes(self):
        with self.assertRaisesRegex(ValueError, "not valid UTF-8"):
            screen_identity(b"\xff", self.md5, self.pc_bytes)

    def test_bounded_device_info(self):
        with self.assertRaisesRegex(ValueError, "invalid device_info size"):
            screen_identity(b"x" * 131073, self.md5, self.pc_bytes)

    def test_invalid_serial_port_blocks_before_read(self):
        with self.assertRaisesRegex(ValueError, "explicit COMn"):
            check_device("COM0", Path("/not-used"), Path("/not-used"))

if __name__ == "__main__":
    unittest.main()
