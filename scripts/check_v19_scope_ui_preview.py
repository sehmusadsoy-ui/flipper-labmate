#!/usr/bin/env python3
"""Verify isolated v1.9 Scope simulated UX cannot operate physical GPIO."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
demo = root / "tests/flipper_scope_ui_preview"
manifest = (demo / "application.fam").read_text()
src = (demo / "preview.c").read_text()
prod = (root / "application.fam").read_text()
assert 'appid="labmate_scopeuipreview"' in manifest
assert 'sources=["preview.c"]' in manifest
assert 'fap_category="Tools"' in manifest
assert 'entry_point="labmate_scope_ui_preview_app"' in manifest
assert 'appid="labmate"' in prod and 'sources=["src/*.c"]' in prod
assert "labmate_scopeuipreview" not in prod

for forbidden in (
    "furi_hal_gpio", "furi_hal_i2c", "furi_hal_serial",
    "furi_hal_ibutton", "furi_hal_power", "furi_hal_resources",
    "power_enable_otg", "gpio_ext_", "gpio_ibutton", "&gpio_",
    "onewire_host_", "furi_hal_spi_", "LL_GPIO_", "stm32wb",
    "TIM1", "TIM2", "FuriHalI2c", "FuriHalSerial",
):
    assert forbidden not in src, f"Unauthorized hardware in Scope preview: {forbidden}"

required = (
    '"../../src/labmate_scope_trace.c"',
    '"../../src/labmate_scope_project.c"',
    "#define SCOPE_UI_SCENES 9U",
    '"SIMULATED - NO GPIO"',
    '"SCOPE UX DEMO"',
    "canvas_draw_box(",
    "LabMateScopeViewOverflow",
    "LabMateScopeViewFault",
    "LabMateScopeViewWaitingTrigger",
    "LabMateScopeViewNotTriggered",
    "LabMateScopeViewNoSpan",
    "LabMateScopeFeedOverflow",
    "LabMateScopeFeedFault",
    "furi_mutex_acquire(demo->lock, FuriWaitForever)",
    "furi_mutex_release(demo->lock)",
    "furi_message_queue_put(queue, event, 0U)",
    "InputKeyBack",
    "InputKeyLeft",
    "InputKeyRight",
)
for req in required:
    assert req in src, f"Scope preview lacks mandatory UX/isolation element: {req}"

# Label must be unconditionally drawn in Canvas callback before any
# waveform conditional branch, so none of nine scenes can hide it.
draw = src.split("static void demo_draw(", 1)[1].split("static void demo_input(", 1)[0]
label = draw.index('"SIMULATED - NO GPIO"')
first_branch = draw.index("if(!ok)")
assert label < first_branch
assert "gui_add_view_port" in src and "gui_remove_view_port" in src
assert "view_port_enabled_set(viewport, false)" in src

# Keep Scope UI as a separate FAP, never accidentally linked into LabMate.
production_names = {p.name for p in (root / "src").iterdir()}
assert "preview.c" not in production_names
print("v1.9 Scope simulated UI static guard: 9 scenes, permanent label, no GPIO/bus, isolated FAP PASS")
