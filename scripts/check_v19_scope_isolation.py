#!/usr/bin/env python3
"""v1.9 Scope CORE ONLY: no hidden GPIO capture or advertised live Scope UI."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
src_dir = root / "src"
header = (src_dir / "labmate_scope_trace.h").read_text()
source = (src_dir / "labmate_scope_trace.c").read_text()
tests = (root / "tests/test_scope_trace.c.inc").read_text()
manifest = (root / "application.fam").read_text()

for forbidden in (
    "#include <furi", "#include <stm32", "furi_", "Furi", "gpio_", "Gpio",
    "HAL_", "TIM1", "TIM2", "LL_", "canvas_", "storage_", "malloc(",
    "realloc(", "free(", "thread_", "FuriWaitForever", "power_enable_",
):
    assert forbidden not in source, f"Scope pure model has hardware dependency: {forbidden}"

for phrase in (
    "#define LABMATE_SCOPE_MAX_EVENTS 128U",
    "LABMATE_SCOPE_MAX_SPAN_TICKS",
    "LabMateScopeTriggerRising",
    "LabMateScopeTriggerFalling",
    "LabMateScopeTriggerEither",
    "LabMateScopeOverflow",
    "LabMateScopeFaultClock",
    "missed_lower_bound",
    "generation",
):
    assert phrase in header, phrase
for phrase in (
    "trace->generation == UINT32_MAX",
    "delta > LABMATE_SCOPE_MAX_SPAN_TICKS",
    "delta > LABMATE_SCOPE_MAX_SPAN_TICKS - trace->elapsed_ticks",
    "trace->missed_lower_bound = 1U",
    "trace->state = LabMateScopeOverflow",
    "_Static_assert(sizeof(LabMateScopeEvent) <= 8U",
):
    assert phrase in source, phrase

for phrase in (
    "test_invalid_starts_and_stale_generations();",
    "test_edge_trigger_and_no_fake_pretrigger();",
    "test_wrap_and_clock_failures();",
    "test_buffer_full_without_overwrite();",
    "test_generation_saturation_and_retained_final_state();",
):
    assert phrase in tests, phrase

# The source is part of an unpublished development FAP via wildcard,
# but MUST NOT have GPIO/ISR/menu routing yet.
assert 'sources=["src/*.c"]' in manifest
all_app_files = sorted(src_dir.glob("*.c")) + sorted(src_dir.glob("*.h"))
for path in all_app_files:
    if path.name in ("labmate_scope_trace.c", "labmate_scope_trace.h"):
        continue
    s = path.read_text()
    for expression in (
        r"\blabmate_scope_trace_(start|feed|stop)\s*\(",
        r"\bLabMateToolScope\b",
        r"\bLabMateScreenScope\b",
    ):
        assert re.search(expression, s) is None, f"Unexpected scope integration: {path} {expression}"

print("v1.9 Scope trace: HAL-free, bounded and NOT connected to physical GPIO/menu PASS")
