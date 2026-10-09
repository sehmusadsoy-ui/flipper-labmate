#!/usr/bin/env python3
"""Static architecture guards for LabMate v1.6 development.

These guards do not replace a Momentum SDK compile or Flipper hardware tests.
They verify source-module boundaries after the view-only screen extraction.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "labmate.c").read_text(encoding="utf-8")
SCREENS = (ROOT / "labmate_ui_screens.c").read_text(encoding="utf-8")
SCREENS_H = (ROOT / "labmate_ui_screens.h").read_text(encoding="utf-8")
INTERNAL_H = (ROOT / "labmate_internal.h").read_text(encoding="utf-8")
PRIMITIVES = (ROOT / "labmate_ui_primitives.c").read_text(encoding="utf-8")
MANIFEST = (ROOT / "application.fam").read_text(encoding="utf-8")
POLICY = (ROOT / "labmate_resource_policy.c").read_text(encoding="utf-8")
POLICY_H = (ROOT / "labmate_resource_policy.h").read_text(encoding="utf-8")


failures: list[str] = []


def expect(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


SCREENS_EXPECTED = [
    "draw_menu",
    "draw_gpio",
    "draw_frequency",
    "draw_pulse",
    "draw_generator",
    "draw_logger",
    "draw_history",
    "draw_history_detail",
    "draw_about",
]

for name in SCREENS_EXPECTED:
    implementation = rf"(?m)^void\s+{name}\s*\("
    expect(
        len(re.findall(implementation, SCREENS)) == 1,
        f"{name}: expected one external renderer in labmate_ui_screens.c",
    )
    expect(
        len(re.findall(rf"\b{re.escape(name)}\s*\(", SCREENS_H)) == 1,
        f"{name}: expected one declaration in labmate_ui_screens.h",
    )
    expect(
        not re.search(rf"(?m)^(?:static\s+)?void\s+{name}\s*\(", MAIN),
        f"{name}: stale definition in labmate.c",
    )
    expect(
        len(re.findall(rf"\b{re.escape(name)}\s*\(canvas", MAIN)) == 1,
        f"{name}: expected exactly one render-callback dispatch",
    )

# Screen drawing must not itself open files, change hardware configuration,
# acquire a second mutex or manipulate EXTI lines.
for pattern in [
    r"\bstorage_\w+\s*\(",
    r"\bfuri_hal_\w+\s*\(",
    r"\bfuri_mutex_\w+\s*\(",
    r"\bLL_(?:TIM|EXTI)_\w+\s*\(",
    r"\b(?:logger_start|logger_stop|frequency_hw_start|generator_start)\s*\(",
]:
    expect(
        re.search(pattern, SCREENS) is None,
        f"View-only module contains a prohibited operation: {pattern}",
    )

# Preserve the original single implementations and shared lookup tables.
expect(
    len(re.findall(r"(?m)^uint64_t\s+pulse_cycles_to_us\s*\(", MAIN)) == 1,
    "The original pulse unit-conversion implementation must remain in core",
)
expect(
    "uint64_t pulse_cycles_to_us(uint32_t cycles);" in INTERNAL_H,
    "Shared pulse unit-conversion declaration is absent",
)
expect(
    "const uint32_t labmate_generator_frequencies[]" in MAIN
    and "extern const uint32_t labmate_generator_frequencies[]" in INTERNAL_H,
    "Shared generator presets must have one core definition",
)
expect(
    "const char* const labmate_gpio_names[GPIO_COUNT]" in SCREENS
    and "extern const char* const labmate_gpio_names[GPIO_COUNT]" in INTERNAL_H,
    "GPIO labels must remain shared across display screens",
)
for name in ["ui_badge", "ui_key", "ui_draw_menu_icon", "ui_draw_header"]:
    expect(
        len(re.findall(rf"(?m)^void\s+{name}\s*\(", PRIMITIVES)) == 1,
        f"UI primitive is missing: {name}",
    )

for sentinel in [
    "static void frequency_gpio_callback(",
    "static void pulse_gpio_callback(",
    "static void frequency_hw_start(",
    "static void frequency_hw_stop(",
    "static void generator_start(",
    "static void generator_stop(",
    "static bool logger_start(",
    "static void logger_stop(",
    "static void history_scan(",
    "static void history_read_step(",
    "storage_file_write(",
]:
    expect(sentinel in MAIN, f"Required capture/storage function missing: {sentinel}")

expect('"v1.6d"' in INTERNAL_H, "Development UI version must remain v1.6d")
expect('fap_version="1.6"' in MANIFEST, "Development manifest must remain 1.6")
expect(
    'sources=["*.c"]' in MANIFEST,
    "FAP source list must explicitly exclude native C test fixtures",
)
expect(
    (ROOT / "tests/test_resource_policy.c.inc").is_file()
    and not (ROOT / "tests/test_resource_policy.c").exists(),
    "Native PA7 tests must not be included as a FAP .c translation unit",
)
expect('"3.3V GPIO ONLY"' in SCREENS, "Safety indication missing from About screen")

# A background TIM1 PWM output owns PA7. The GPIO Monitor must not
# reconfigure that pin (including on entry with a stale PA7 selection).
expect(
    "labmate_monitor_entry_pin(app->gpio_index, app->generator_running)" in MAIN,
    "GPIO Monitor entry must respect background PA7 ownership",
)
expect(
    "labmate_monitor_next_pin(app->gpio_index, direction, app->generator_running)" in MAIN,
    "GPIO Monitor navigation must skip reserved PA7",
)
expect(
    "labmate_monitor_pin_allowed(index, app->generator_running)" in MAIN,
    "GPIO release must not reconfigure a reserved PA7 PWM output",
)
expect(
    "static void gpio_release(LabMateApp* app, uint8_t index)" in MAIN,
    "GPIO release must receive app ownership context",
)
expect(
    '"PA7 BUSY"' in SCREENS,
    "GPIO Monitor should explain that PWM has reserved PA7",
)
expect(
    "labmate_monitor_pin_allowed(" in POLICY
    and "labmate_monitor_entry_pin(" in POLICY
    and "labmate_monitor_next_pin(" in POLICY,
    "Missing shared portable resource policy implementation",
)
expect(
    "#define LABMATE_MONITOR_PA7_INDEX 7U" in POLICY_H,
    "Incorrect reserved PA7 GPIO monitor index",
)


if failures:
    for error in failures:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print(f"LabMate v1.6 boundaries OK: {len(SCREENS_EXPECTED)} view-only screens")
print("GPIO/IRQ, PWM and microSD implementation retained in app core")
print("NOTE: static checks cannot verify behavior on the physical Flipper")
