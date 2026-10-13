#!/usr/bin/env python3
"""L1 128x64 scope projection remains HAL-free and separated from UI."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
src = root / "src"
header = (src / "labmate_scope_project.h").read_text()
code = (src / "labmate_scope_project.c").read_text()
tests = (root / "tests/test_scope_project.c.inc").read_text()
fam = (root / "application.fam").read_text()

for forbidden in (
    "#include <furi", "furi_", "Furi", "furi_hal_", "gpio_", "Gpio",
    "canvas_", "view_port_", "thread_", "TIM1", "TIM2", "LL_",
    "power_enable_", "storage_", "malloc(", "free(", "realloc(",
):
    assert forbidden not in code, f"L1 projection hardware/UI dependency: {forbidden}"

for required in (
    "LABMATE_SCOPE_GRAPH_COLUMNS 120U",
    "LabMateScopeViewWaitingTrigger",
    "LabMateScopeViewNotTriggered",
    "LabMateScopeViewNoSpan",
    "LabMateScopeViewOverflow",
    "LabMateScopeViewFault",
    "dense_columns",
    "right_cropped",
):
    assert required in header, required

for required in (
    "memset(output, 0, sizeof(*output))",
    "trace->event_count > LABMATE_SCOPE_MAX_EVENTS",
    "trace->events[trace->event_count - 1U].offset_ticks",
    "if(window_end_ticks > last_known) return false;",
    "trace->events[next].offset_ticks <= window_start_ticks",
    "(uint64_t)relative",
    "if(col->transitions >= 2U)",
    "trace->state == LabMateScopeOverflow",
):
    assert required in code, required

for required in (
    "test_edges_scale_and_no_synthetic_pulses();",
    "test_dense_columns_never_render_fake_clean_pulse();",
    "test_crop_and_exact_right_endpoint();",
    "test_no_trigger_no_span_fault_and_invalid();",
    "test_overflow_unknown_tail_never_drawn();",
    "test_large_tick_span_uses_64_bit_math();",
):
    assert required in tests, required

assert 'sources=["src/*.c"]' in fam
assert 'fap_version="1.8"' in fam  # no premature 1.9 version label
for path in src.glob("*"):
    if path.name in ("labmate_scope_project.c", "labmate_scope_project.h") or path.suffix not in (".c", ".h"):
        continue
    data = path.read_text()
    for expr in (r"\blabmate_scope_project\s*\(", r"\bLabMateToolScope\b", r"\bLabMateScreenScope\b"):
        assert re.search(expr, data) is None, f"L1 prematurely activated {path.name}: {expr}"
print("v1.9 Scope L1 projection static guard: pure 120-column model, no live UI or GPIO PASS")
