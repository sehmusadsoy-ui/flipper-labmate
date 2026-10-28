#!/usr/bin/env python3
"""Final E11 Button/Scope UI integration SOURCE-CONTRACT gate, not device validation.

The assertions deliberately inspect real input, view and pair renderer bodies.
No FAP installation, file management, firmware, GPIO or runtime calls.
"""
from pathlib import Path

R = Path(__file__).resolve().parent.parent
def src(path): return (R/path).read_text(encoding="utf-8")
def require(body, snippets, name):
    for needle in snippets:
        assert needle in body, f"{name}: missing source safety gate {needle!r}"
def forbid(body, snippets, name):
    for needle in snippets:
        assert needle not in body, f"{name}: unexpected side effect {needle!r}"
def fn(code, signature):
    pos = code.find(signature)
    assert pos >= 0 and code.find(signature, pos+1) < 0, signature
    open_brace = code.index("{", pos)
    depth = 0
    for j in range(open_brace, len(code)):
        if code[j] == "{": depth += 1
        if code[j] == "}":
            depth -= 1
            if depth == 0: return code[pos:j+1]
    raise AssertionError(f"unclosed function: {signature}")

input_code=fn(src("src/labmate_scope_bridge.c"),
              "void labmate_scope_bridge_input(")
stop_code=fn(src("src/labmate_scope_bridge.c"),
             "bool labmate_scope_bridge_stop(")
view_code=src("src/labmate_view.c")
pair_code=fn(src("src/labmate_scope_pair_view.c"),
             "bool labmate_scope_pair_view_draw(")
scope_code=fn(src("src/labmate_scope_display.c"),
              "bool labmate_scope_display_draw(")
ref_code=fn(src("src/labmate_scope_reference_view.c"),
            "bool labmate_scope_reference_view_draw(")
button_code=fn(src("src/labmate_ui_screens.c"),"void draw_button(")

# Four-page controller behavior: DOWN only if inactive, reference UP changes
# only target, detail UP toggles the stored A/B source; LEFT and RIGHT use
# the legitimate pair_save_a/b and cannot store during active capture.
require(input_code, (
    "event.key == InputKeyDown && !a->scope_native.active",
    "if(a->scope_show_reference)",
    "a->scope_show_reference = false;",
    "a->scope_show_compare = false;",
    "a->scope_show_details = false;",
    "a->scope_show_compare = true;",
    "a->scope_compare_page = 0U;",
    "a->scope_show_details = true;",
    "a->scope_compare_page = 1U;",
    "event.key == InputKeyUp && !a->scope_native.active",
    "a->scope_compare_page == 1U ? 2U : 1U",
    "LabMateScopeReference1kHz50",
    "event.key == InputKeyLeft || event.key == InputKeyRight",
    "!a->scope_native.active && !a->scope_show_reference",
    "a->scope_last_valid &&",
    "labmate_scope_native_reinit_safe(&a->scope_native)",
    "a->capture_owner == LabMateCaptureNone",
    "a->scope_last_generation == a->scope_capture_generation",
    "labmate_scope_pair_save_a(",
    "labmate_scope_pair_save_b(",
    "if(event.key != InputKeyOk) return;",
    "if(a->scope_native.active) {",
    "labmate_scope_bridge_stop(a);",
    "a->scope_capture_generation == UINT32_MAX",
), "Scope input")

assert "if(labmate_scope_bridge_stop(a))\n            a->screen = LabMateScreenMenu;" in input_code, \
       "Scope BACK must fail closed on release fault"
require(stop_code, (
    "labmate_scope_native_stop_confirmed(",
    "a->capture_release_fault = true;",
    "a->capture_blocked = true;",
    "a->scope_last_valid = false;",
    "labmate_scope_bridge_latch(a);",
), "Scope STOP")
assert stop_code.index("labmate_scope_native_stop_confirmed(") < \
       stop_code.index("labmate_scope_bridge_latch(a);")

# Actual frame dispatch checks native lease, generation and clock before
# exposing historical capture as current, or passing it to the renderer.
require(view_code, (
    "labmate_scope_native_reinit_safe(&app->scope_native)",
    "app->capture_owner == LabMateCaptureNone;",
    "app->scope_last_generation == app->scope_capture_generation",
    "app->scope_last_valid && !app->scope_clock_fault",
    "LabMateScopeObservationNoSignalConfirmed",
    "labmate_scope_tolerance_evaluate(&reference, measured, observation)",
    "labmate_scope_native_stop_confirmed(",
    'canvas_draw_str(canvas, 3, 23, "SCOPE IRQ FAULT")',
    "app->scope_last_generation > app->scope_pair.generation_a",
    "labmate_scope_pair_view_draw(",
    "display.completed = NULL;",
    "display.completed = &app->scope_last_metrics;",
), "Scope view dispatcher")

# Pair renderer cannot synthesize captured waveform or repurpose percentage
# as signed frequency delta. Empty-state dotted art is purely decorative.
require(pair_code, (
    "p->generation_a == 0U",
    "p->generation_b <= p->generation_a",
    "!metric_valid(&p->a)", "!metric_valid(&p->b)",
    "p->delta.frequency_delta_millihz",
    "frequency(val, sizeof(val), mag)",
    "p->has_a ? af : \"Empty\"",
    "p->has_b ? bf : \"Empty\"",
    "ui_kit_pulse_line_dotted(",
    "ui_kit_scope_page_dots(",
    "ui_kit_next_cue(",
), "Compare + Sample renderer")
assert pair_code.count("ui_kit_pulse_line_dotted(") == 1, \
       "No reconstructed capture wave should appear on filled Sample A/B"

require(ref_code, (
    "labmate_scope_tolerance_evaluate(",
    "LabMateScopeObservationComplete",
    "LabMateScopeVerdictPass",
    "LabMateScopeVerdictOutOfTolerance",
    "LabMateScopeVerdictBusy",
    "ui_kit_scope_page_dots(",
), "Reference renderer")
require(scope_code, (
    "ui_kit_pulse_line_dotted(",
    "d->plot.line_count",
    "d->lines[i]",
    "ui_kit_pixel_header(",
    "ui_kit_scope_page_dots(",
    "if(!active)",
), "Scope renderer")
require(button_code, (
    "ui_kit_pixel_header(",
    "button_stats.stable_level",
    "button_stats.pending",
    "button_stats.releases",
    "button_session_started",
    "UiKitKeyDown",
    "UiKitKeyOk",
    "capture_release_fault",
), "Button renderer")

for name,body in (
    ("Button",button_code),
    ("Scope",scope_code),
    ("Reference",ref_code),
    ("Compare/Sample",pair_code),
):
    forbid(body, (
        "furi_hal_gpio_", "furi_hal_resource_lease_",
        "storage_file_write(", "labmate_scope_native_start(",
        "labmate_scope_pair_save_a(", "labmate_scope_pair_save_b(",
    ),name)

fam=src("application.fam")
assert 'fap_version="2.0"' in fam, "v2.0 application manifest changed"
print("FINAL E11 UI INTEGRATION SOURCE PASS: Button/Scope/Reference/Compare/Sample")
print("CHECKED: STOP/BACK native ownership, four-page routing, authentic A/B,")
print("validated/reference data only, distinct errors, display-side no writes")
print("NOT PROVEN: 128x64 real raster, physical PC1/IRQ, USB, SD, Stable release")
