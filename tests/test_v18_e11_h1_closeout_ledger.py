#!/usr/bin/env python3
"""Repository-only E11 H1 ledger: never promote a host/software PASS to device PASS.

Reads static Markdown and checked-in source; no USB, GPIO, artifacts,
firmware execution, SD access or user data.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/V1_8_E11_H1_CLOSEOUT_DECISION_2026-10-17.md"
HOST = ROOT / "tests/test_v18_e11_h1_pwm_js_joint.py"
FLOW = ROOT / ".github/workflows/check-v18-e11-h1-pwm-js-joint.yml"

REQUIRED = (
    "**NOT OBSERVED / BLOCKED**",
    "36/36",
    "H0: **PASS**",
    "H2: **PASS**",
    "H1",
    "CLI",
    "CliCommandFlagDefault",
    "CliCommandFlagParallelSafe",
    "loader_lock(loader)",
    "LL_GPIO_GetPinMode",
    "furi_hal_gpio_read",
    "not on-device firmware",
    "no binary update",
    "No permission exists",
)

def audit(ledger: str, test: str, workflow: str) -> None:
    """Fail closed if exact scoped evidence/wording is silently dropped."""
    for marker in REQUIRED:
        if marker.lower() not in ledger.lower():
            raise ValueError("E11 H1 ledger safety marker absent: " + marker)
    if "simultaneous second-client PA7 BUSY** | **NOT OBSERVED / BLOCKED**" not in ledger:
        raise ValueError("E11 H1 device BUSY result must remain explicitly BLOCKED")
    if "**H1 DEVICE PASS**" in ledger.upper():
        raise ValueError("E11 H1 real-device acceptance was not observed")
    for token in ("js_cli=", "gpio_cli=", "gpio_read=", "loader_lock(loader)",
                  "extract_js_claim(js)", "JS_RUN+helper", "furi_hal_pwm_is_running"):
        if token not in test:
            raise ValueError("H1 original-C, CLI guard or mock test removed: " + token)
    if "test_v18_e11_h1_pwm_js_joint.py" not in workflow:
        raise ValueError("H1 source test omitted from CI")
    for token in ("NO DEVICE", "NO", "momentum-src"):
        if token not in workflow:
            raise ValueError("H1 dedicated job description/source missing: " + token)


class H1LedgerGateTests(unittest.TestCase):
    def test_repo_ledger_is_fail_closed(self):
        audit(LEDGER.read_text(), HOST.read_text(), FLOW.read_text())

    def test_cannot_promote_live_result(self):
        doc=LEDGER.read_text()
        with self.assertRaisesRegex(ValueError,"BLOCKED"):
            audit(doc.replace("**NOT OBSERVED / BLOCKED**", "**PASS**"),
                  HOST.read_text(), FLOW.read_text())

    def test_cannot_erase_cli_read_bypass_evidence(self):
        doc=LEDGER.read_text()
        with self.assertRaisesRegex(ValueError,"safety marker"):
            audit(doc.replace("LL_GPIO_GetPinMode","mode-register-probe"),
                  HOST.read_text(), FLOW.read_text())

    def test_cannot_remove_original_c_js_claim(self):
        src=HOST.read_text()
        with self.assertRaisesRegex(ValueError,"source"):
            audit(LEDGER.read_text(),src.replace("extract_js_claim(js)","mock_claim()"),
                  FLOW.read_text())


if __name__ == "__main__":
    unittest.main()
