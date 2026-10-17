"""Negative build-gate tests; no device access or firmware source changes."""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.verify_v19_e11_sdk_fap import VerificationError, verify_fap, verify_sources


class BuildGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write("targets/f7/api_symbols.csv", """Function,+,furi_hal_resource_lease_try_acquire,uint32_t,uint32_t
Function,+,furi_hal_resource_lease_release,_Bool,"uint32_t, uint32_t"
Function,+,furi_hal_gpio_try_add_int_callback,_Bool,"const GpioPin*, GpioExtiCallback, void*"
""")
        self.write("targets/f7/furi_hal/furi_hal_resources.h", """#define FURI_HAL_RESOURCE_LEASE_API_V1 1
#define FURI_HAL_LEASE_IRQ_PC1 999
""")
        self.write("targets/f7/furi_hal/furi_hal_gpio.h", "#define FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK 1\n")
        self.write("applications_user/labmate/application.fam", 'fap_version="1.9",\n')
        self.write("applications_user/labmate/src/labmate_internal.h", '#define LABMATE_VERSION_TEXT "v1.9DEV"\n')
        self.write("applications_user/labmate/src/labmate_scope_native.c", "furi_hal_resource_lease_try_acquire(lease);\nfuri_hal_gpio_try_add_int_callback(pin, cb, context);\n")
        elf = bytearray(512)
        elf[:6] = b"\x7fELF\x01\x01"
        elf[18:20] = (40).to_bytes(2, "little")
        self.write("labmate.fap", bytes(elf))

    def write(self, rel, content):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if isinstance(content, bytes) else content.encode())

    def test_valid_sdk_and_binary(self):
        verify_sources(self.root)
        size, sha = verify_fap(self.root / "labmate.fap")
        self.assertEqual(size, 512)
        self.assertEqual(sha, hashlib.sha256((self.root / "labmate.fap").read_bytes()).hexdigest())

    def test_missing_export_fails(self):
        p = self.root / "targets/f7/api_symbols.csv"
        p.write_text(p.read_text().replace("Function,+,furi_hal_resource_lease_release", "Function,-,furi_hal_resource_lease_release"))
        with self.assertRaisesRegex(VerificationError, "furi_hal_resource_lease_release"):
            verify_sources(self.root)

    def test_missing_native_feature_macro_fails(self):
        self.write("targets/f7/furi_hal/furi_hal_gpio.h", "/* unpatched */\n")
        with self.assertRaisesRegex(VerificationError, "callback ABI macro"):
            verify_sources(self.root)

    def test_wrong_fap_version_fails(self):
        self.write("applications_user/labmate/application.fam", 'fap_version="1.8",\n')
        with self.assertRaisesRegex(VerificationError, "not v1.9DEV"):
            verify_sources(self.root)

    def test_legacy_asserting_gpio_fallback_fails(self):
        p = "applications_user/labmate/src/labmate_scope_native.c"
        self.write(p, "furi_hal_resource_lease_try_acquire(lease);\nfuri_hal_gpio_try_add_int_callback(p,c,k);\nfuri_hal_gpio_add_int_callback(p,c,k);\n")
        with self.assertRaisesRegex(VerificationError, "legacy asserting"):
            verify_sources(self.root)

    def test_bad_fap_and_wrong_arch_fail(self):
        self.write("labmate.fap", b"\0" * 512)
        with self.assertRaisesRegex(VerificationError, "not an ELF"):
            verify_fap(self.root / "labmate.fap")
        e = bytearray(512)
        e[:6] = b"\x7fELF\x01\x01"
        e[18:20] = (62).to_bytes(2, "little")
        self.write("labmate.fap", bytes(e))
        with self.assertRaisesRegex(VerificationError, "not ARM"):
            verify_fap(self.root / "labmate.fap")


if __name__ == "__main__":
    unittest.main()
