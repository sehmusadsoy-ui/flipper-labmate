#!/usr/bin/env python3
"""Fail-closed source-only regression for the E11 v1.8 release gate.

This suite is NOT a release approval mechanism. It asserts that the
documentation distinguishes host C evidence, real-device observed
functions, and pending release and fixture gates. No USB/SD/firmware.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/V1_8_E11_RELEASE_READINESS_2026-10-17.md"
DEFERRED = ROOT / "docs/DEFERRED_HARDWARE_TESTS.md"
ROADMAP = ROOT / "ROADMAP.md"
H1 = ROOT / "docs/V1_8_E11_H1_CLOSEOUT_DECISION_2026-10-17.md"

REQUIRED = (
    "FULL STABLE UPDATE NOT READY",
    "36/36",
    "H0",
    "H2",
    "H1",
    "NOT OBSERVED",
    "DEV",
    "119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0",
    "2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0",
    "101 / 101",
    "UART",
    "Logger/Profile",
    "HW-06",
    "HW-07",
    "EXPLICIT",
    "NO-GO",
    "v1.9",
)

def audit(release: str, backlog: str, roadmap: str, h1: str) -> None:
    for marker in REQUIRED:
        if marker.lower() not in release.lower():
            raise ValueError("E11 release condition evidence missing: " + marker)
    if "H1 on-device simultaneous" not in release or "NOT OBSERVED" not in release:
        raise ValueError("Real H1 concurrent device BUSY cannot silently become PASS")
    for token in ("**DEFERRED", "DS18B20", "ACK", "NOT PASSED",
                  "H1", "NO-GO"):
        if token.lower() not in backlog.lower() + release.lower():
            raise ValueError("Hardware deferral exception removed: " + token)
    if "deferred / not passed" not in roadmap.lower():
        raise ValueError("Agreed roadmap hardware deferral status missing")
    if "**NOT OBSERVED / BLOCKED**" not in h1:
        raise ValueError("H1 concurrent device result was not PASS")
    if "published Stable tag" not in release:
        raise ValueError("Published v1.8 Stable immutability not described")


class ReleaseReadinessGuard(unittest.TestCase):
    def test_current_e11_release_stays_gated(self):
        audit(DOC.read_text(), DEFERRED.read_text(), ROADMAP.read_text(), H1.read_text())

    def test_cannot_relabel_h1_as_device_pass(self):
        s = DOC.read_text()
        with self.assertRaisesRegex(ValueError, "NOT OBSERVED|H1"):
            audit(s.replace("H1 on-device simultaneous", "H1 on-device completed"),
                  DEFERRED.read_text(), ROADMAP.read_text(), H1.read_text())

    def test_cannot_mark_release_ready_by_deleting_no_go(self):
        s = DOC.read_text().replace("NO-GO", "READY")
        with self.assertRaisesRegex(ValueError, "NO-GO"):
            audit(s, DEFERRED.read_text(), ROADMAP.read_text(), H1.read_text())

    def test_cannot_drop_production_identity(self):
        s = DOC.read_text().replace(
            "119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0", "")
        with self.assertRaisesRegex(ValueError, "119c44"):
            audit(s, DEFERRED.read_text(), ROADMAP.read_text(), H1.read_text())


if __name__ == "__main__":
    unittest.main()
