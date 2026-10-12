#!/usr/bin/env python3
"""Static architecture guards for LabMate v1.6 development.

These guards do not replace a Momentum SDK compile or Flipper hardware tests.
They verify source-module boundaries after the view-only screen extraction.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
COORDINATOR = (SRC / "labmate.c").read_text(encoding="utf-8")
INPUT_DISPATCH = (SRC / "labmate_input.c").read_text(encoding="utf-8")
CAPTURE_SESSION = (SRC / "labmate_capture_session.c").read_text(encoding="utf-8")
VIEW_COORDINATOR = (SRC / "labmate_view.c").read_text(encoding="utf-8")
DEFERRED_IO = (SRC / "labmate_deferred.c").read_text(encoding="utf-8")
# v1.6/v1.7 boundary assertions follow operations across the new
# coordinator modules, rather than assuming all were inside labmate.c.
SCREEN_HANDLERS = "\n".join(
    (SRC / filename).read_text(encoding="utf-8") for filename in (
        "labmate_input_menu.c", "labmate_input_profiles.c",
        "labmate_input_history.c", "labmate_input_measure.c",
        "labmate_input_output.c"))
MAIN = "\n".join((COORDINATOR, INPUT_DISPATCH, SCREEN_HANDLERS,
                  CAPTURE_SESSION, VIEW_COORDINATOR, DEFERRED_IO))
MEASUREMENTS = (SRC / "labmate_measurements.c").read_text(encoding="utf-8")
MEASUREMENTS_H = (SRC / "labmate_measurements.h").read_text(encoding="utf-8")
LOGGER_SNAPSHOT = (SRC / "labmate_logger_snapshot.c").read_text(encoding="utf-8")
LOGGER_SNAPSHOT_H = (SRC / "labmate_logger_snapshot.h").read_text(encoding="utf-8")
ALERT_BRIDGE = (SRC / "labmate_alerts_bridge.c").read_text(encoding="utf-8")
ALERT_BRIDGE_H = (SRC / "labmate_alerts_bridge.h").read_text(encoding="utf-8")
GENERATOR = (SRC / "labmate_generator.c").read_text(encoding="utf-8")
GENERATOR_H = (SRC / "labmate_generator.h").read_text(encoding="utf-8")
TIM2_CAPTURE = (SRC / "labmate_frequency_tim2.c").read_text(encoding="utf-8")
TIM2_CAPTURE_H = (SRC / "labmate_frequency_tim2.h").read_text(encoding="utf-8")
EXTI_CAPTURE = (SRC / "labmate_capture_exti.c").read_text(encoding="utf-8")
EXTI_CAPTURE_H = (SRC / "labmate_capture_exti.h").read_text(encoding="utf-8")
CAPTURE_CORE = (SRC / "labmate_capture_core.c").read_text(encoding="utf-8")
CAPTURE_CORE_H = (SRC / "labmate_capture_core.h").read_text(encoding="utf-8")
PULSE_CAPTURE = (SRC / "labmate_pulse_capture.c").read_text(encoding="utf-8")
PULSE_CAPTURE_H = (SRC / "labmate_pulse_capture.h").read_text(encoding="utf-8")
FREQ_CAPTURE = (SRC / "labmate_frequency_capture.c").read_text(encoding="utf-8")
FREQ_CAPTURE_H = (SRC / "labmate_frequency_capture.h").read_text(encoding="utf-8")
MONITOR_GPIO = (SRC / "labmate_monitor_gpio.c").read_text(encoding="utf-8")
MONITOR_GPIO_H = (SRC / "labmate_monitor_gpio.h").read_text(encoding="utf-8")
COUNTER = (SRC / "labmate_event_counter.c").read_text(encoding="utf-8")
COUNTER_H = (SRC / "labmate_event_counter.h").read_text(encoding="utf-8")
COUNTER_MATH = (SRC / "labmate_counter_math.c").read_text(encoding="utf-8")
COUNTER_MATH_H = (SRC / "labmate_counter_math.h").read_text(encoding="utf-8")
BUTTON = (SRC / "labmate_button_capture.c").read_text(encoding="utf-8")
BUTTON_H = (SRC / "labmate_button_capture.h").read_text(encoding="utf-8")
BUTTON_LOGIC = (SRC / "labmate_button_logic.c").read_text(encoding="utf-8")
BUTTON_LOGIC_H = (SRC / "labmate_button_logic.h").read_text(encoding="utf-8")
THRESHOLD = (SRC / "labmate_threshold.c").read_text(encoding="utf-8")
THRESHOLD_H = (SRC / "labmate_threshold.h").read_text(encoding="utf-8")
SCREENS = (SRC / "labmate_ui_screens.c").read_text(encoding="utf-8")
SCREENS_H = (SRC / "labmate_ui_screens.h").read_text(encoding="utf-8")
INTERNAL_H = (SRC / "labmate_internal.h").read_text(encoding="utf-8")
PRIMITIVES = (SRC / "labmate_ui_primitives.c").read_text(encoding="utf-8")
NAVIGATION = (SRC / "labmate_navigation.c").read_text(encoding="utf-8")
MANIFEST = (ROOT / "application.fam").read_text(encoding="utf-8")
PROFILES = (SRC / "labmate_profiles.c").read_text(encoding="utf-8")
POLICY = (SRC / "labmate_resource_policy.c").read_text(encoding="utf-8")
FREQUENCY_GATE = (SRC / "labmate_frequency_gate.c").read_text(encoding="utf-8")
POLICY_H = (SRC / "labmate_resource_policy.h").read_text(encoding="utf-8")
LOGGER_STORAGE = (SRC / "labmate_logger_storage.c").read_text(encoding="utf-8")
LOGGER_STORAGE_H = (SRC / "labmate_logger_storage.h").read_text(encoding="utf-8")


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
    "draw_counter",
    "draw_button",
    "draw_alerts",
    "draw_logger",
    "draw_history",
    "draw_history_detail",
    "draw_about",
    "draw_profiles",
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
    len(re.findall(r"(?m)^uint64_t\s+pulse_cycles_to_us\s*\(", MEASUREMENTS)) == 1,
    "The original pulse unit-conversion implementation must remain in core",
)
expect(
    "uint64_t pulse_cycles_to_us(uint32_t cycles);" in INTERNAL_H,
    "Shared pulse unit-conversion declaration is absent",
)
expect(
    "const uint32_t labmate_generator_frequencies[]" in GENERATOR
    and "const uint32_t labmate_generator_frequencies[]" not in MAIN
    and "extern const uint32_t labmate_generator_frequencies[]" in INTERNAL_H,
    "Shared generator presets must have one definition in generator module",
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

# Every capture start must use the shared exclusive-owner policy.
expect(
    "LabMateCaptureOwner capture_owner;" in INTERNAL_H,
    "Missing exclusive capture owner state",
)
expect(
    FREQ_CAPTURE.count("labmate_capture_can_start(app, LabMateCapture") == 2
    and PULSE_CAPTURE.count("labmate_capture_can_start(app, LabMateCapturePulse)") == 1,
    "All three capture start paths must check ownership and pin eligibility",
)
for owner in (
    "LabMateCaptureFrequencyLow",
    "LabMateCaptureFrequencyHigh",
    "LabMateCapturePulse",
):
    expect(
        f"app->capture_owner = {owner};" in (PULSE_CAPTURE if owner == "LabMateCapturePulse" else FREQ_CAPTURE),
        f"Capture start must mark active owner: {owner}",
    )
expect(
    "labmate_capture_can_acquire(" in POLICY and
    "labmate_capture_pin_allowed(" in POLICY,
    "Exclusive capture policy implementation is missing",
)
expect(
    "app->capture_owner = LabMateCaptureNone;" in MAIN,
    "Capture owner is not cleared after release",
)

# IRQ callback and teardown must reference the actual registered pin.
expect(
    "uint8_t capture_pin_index;" in INTERNAL_H and
    "bool capture_blocked;" in INTERNAL_H,
    "Missing pinned IRQ identity and blocked capture state",
)
expect(
    FREQ_CAPTURE.count("labmate_gpio_pins[app->capture_pin_index]") >= 1
    and PULSE_CAPTURE.count("labmate_gpio_pins[app->capture_pin_index]") >= 2,
    "Active IRQ callback and teardown must use the registered pin",
)
expect(
    FREQ_CAPTURE.count("app->capture_pin_index = app->gpio_index;") == 2
    and PULSE_CAPTURE.count("app->capture_pin_index = app->gpio_index;") == 1,
    "Each capture start path must record its actual selected pin",
)
expect(
    "app->capture_pin_index = GPIO_COUNT;" in MAIN,
    "Capture teardown must invalidate pin identity",
)
expect(
    "app->capture_blocked = !allowed;" in CAPTURE_CORE,
    "Software acquisition denial needs an observable status",
)
expect(
    "labmate_capture_matches(" in POLICY and
    "if(!labmate_capture_matches(" in LOGGER_STORAGE,
    "Logger must verify capture before creating a CSV",
)
expect(
    '"CAPTURE BLOCKED"' in SCREENS and
    'app->capture_blocked ? "ERR"' in SCREENS,
    "Refused capture policy should be visible in UI",
)

# Capture STOP paths share one idempotent teardown helper; Pulse HOLD is
# deliberately excluded because it stops only its own IRQ.
expect(
    CAPTURE_SESSION.count("void labmate_capture_stop_all(LabMateApp* app)") == 1,
    "Unified capture teardown helper must exist exactly once",
)
expect(
    MAIN.count("labmate_capture_stop_all(app);") >= 5,
    "Mode switching, logger, BACK and exit must share capture teardown",
)
expect(
    "void labmate_logger_capture_stop(LabMateApp* app) {\n    labmate_capture_stop_all(app);" in MAIN,
    "Logger stop must call shared teardown",
)
expect(
    "if(labmate_screen_uses_gpio(app->screen)) {\n        labmate_capture_stop_all(app);" in MAIN,
    "App exit must call shared teardown",
)

expect("static void frequency_gpio_callback(" in FREQ_CAPTURE and
       "static void frequency_gpio_callback(" not in MAIN,
       "Frequency GPIO ISR must live in frequency module")
for kind in ("high", "low"):
    for operation in ("start", "stop"):
        name = f"labmate_frequency_{kind}_{operation}"
        expect(len(re.findall(rf"(?m)^void\s+{name}\s*\(", FREQ_CAPTURE)) == 1 and
               f"void {name}(LabMateApp* app);" in FREQ_CAPTURE_H and
               f"{name}(app)" in MAIN,
               f"Frequency lifecycle must be delegated: {name}")

expect("static void pulse_gpio_callback(" in PULSE_CAPTURE and
       "static void pulse_gpio_callback(" not in MAIN,
       "Pulse IRQ callback must live only in pulse module")

# A long HIGH phase must not erase pending short LOW samples (100 Hz / 95%
# duty), nor the opposite phase at 5% duty. This source-level regression
# guard complements the firmware compile and actual on-device pulse test.
asymmetric_phase = re.search(
    r"At extreme duty.*?if\(app->pulse_irq_level\)\s*\{"
    r"(?P<high>.*?)\}\s*else\s*\{(?P<low>.*?)\}\s*\}",
    PULSE_CAPTURE, re.S,
)
expect(
    asymmetric_phase is not None
    and "app->pulse_irq_high_sum = 0U;" in asymmetric_phase.group("high")
    and "app->pulse_irq_high_samples = 0U;" in asymmetric_phase.group("high")
    and "app->pulse_irq_low_sum" not in asymmetric_phase.group("high")
    and "app->pulse_irq_low_samples" not in asymmetric_phase.group("high")
    and "app->pulse_irq_low_sum = 0U;" in asymmetric_phase.group("low")
    and "app->pulse_irq_low_samples = 0U;" in asymmetric_phase.group("low")
    and "app->pulse_irq_high_sum" not in asymmetric_phase.group("low")
    and "app->pulse_irq_high_samples" not in asymmetric_phase.group("low"),
    "Asymmetric duty must preserve the opposite short-phase averaging window",
)
for fn in ("start", "stop"):
    name = f"labmate_pulse_capture_{fn}"
    expect(len(re.findall(rf"(?m)^void\s+{name}\s*\(", PULSE_CAPTURE)) == 1 and
           f"void {name}(LabMateApp* app);" in PULSE_CAPTURE_H and
           f"{name}(app)" in MAIN,
           f"Pulse lifecycle must be delegated: {fn}")
expect("bool labmate_capture_can_start(" in CAPTURE_CORE and
       "bool labmate_capture_can_start(" in CAPTURE_CORE_H and
       "labmate_capture_can_acquire(" in CAPTURE_CORE and
       "const GpioPin* const labmate_gpio_pins[GPIO_COUNT]" in CAPTURE_CORE,
       "Common GPIO mapping and exclusive capture gate must be centralized")

# v1.7 module boundary: PWM HAL ownership belongs to generator.c alone.
for fn in ("start", "stop", "change_frequency"):
    name = f"labmate_generator_{fn}"
    expect(len(re.findall(rf"(?m)^void\s+{name}\s*\(", GENERATOR)) == 1,
           f"{name}: expected exactly one generator implementation")
    expect(f"void {name}(LabMateApp* app" in GENERATOR_H,
           f"{name}: public module declaration missing")
    expect(re.search(rf"\b{re.escape(name)}\s*\(\s*app\b", MAIN) is not None,
           f"{name}: application must delegate to generator module")
expect("furi_hal_pwm_" not in MAIN and "furi_hal_pwm_" not in SCREENS,
       "PWM HAL calls must remain inside generator.c")
for pwm_op in ("furi_hal_pwm_start(", "furi_hal_pwm_stop(", "furi_hal_pwm_set_params("):
    expect(pwm_op in GENERATOR, f"Missing generator HAL operation {pwm_op}")
expect("FuriHalPwmOutputIdTim1PA7" in GENERATOR,
       "Generator must retain TIM1/PA7 ownership")

# True Event Counter must own PB3/TIM2 exclusively, never call GPIO edge IRQs.
expect('LabMateCaptureCounter' in POLICY_H
       and "case LabMateCaptureCounter:" in POLICY
       and "return pin_index == 4U;" in POLICY
       and "LabMateToolCounter" in (SRC / "labmate_navigation.h").read_text(encoding="utf-8")
       and '"Event Counter"' in NAVIGATION,
       "Event Counter must be a distinct PB3-only capture tool")
expect("!app->counter_active && !app->button_active &&" in CAPTURE_CORE
       and "labmate_event_counter_stop(app);" in MAIN
       and "!app->counter_active && !app->button_active && labmate_capture_all_stopped(" in MAIN,
       "Counter ownership must block other capture tools and preserve cleanup")
for name in ("start", "poll", "stop", "reset"):
    decl = f"labmate_event_counter_{name}"
    expect(len(re.findall(rf"(?m)^void\s+{decl}\s*\(", COUNTER)) == 1
           and f"void {decl}(LabMateApp* app);" in COUNTER_H
           and f"{decl}(app);" in MAIN,
           f"Event Counter lifecycle missing {name}")
expect("labmate_frequency_tim2_configure()" in COUNTER
       and "labmate_frequency_tim2_disable()" in COUNTER
       and "labmate_frequency_tim2_shutdown()" in COUNTER
       and "labmate_counter_accumulate(" in COUNTER
       and "furi_hal_gpio_add_int_callback(" not in COUNTER
       and "LL_TIM_" not in COUNTER,
       "Counter must use exclusive hardware TIM2 counting, not GPIO IRQ counting")
expect("labmate_counter_accumulate(" in COUNTER_MATH
       and "labmate_counter_format(" in COUNTER_MATH
       and "uint64_t counter_total;" in INTERNAL_H
       and "labmate_counter_format(app->counter_total" in SCREENS
       and "case LabMateScreenCounter:" in MAIN
       and "case LabMateToolCounter:" in MAIN
       and "case LabMateToolCounter: ui_icon_counter(canvas, x, y);" in PRIMITIVES,
       "64-bit counter accumulation, UI, and navigation must be wired")
expect((ROOT / "tests/test_counter_math.c.inc").is_file()
       and not (ROOT / "tests/test_counter_math.c").exists(),
       "Counter host-native tests must never link into the FAP")


# Button Analyzer must not use EXTI3/6 or claim PA7/PB3.
expect("LabMateCaptureButton" in POLICY_H
       and "case LabMateCaptureButton:" in POLICY
       and "LABMATE_MONITOR_PC1_INDEX" in POLICY
       and "LabMateToolButton" in (SRC / "labmate_navigation.h").read_text(encoding="utf-8")
       and '"Button Analyzer"' in NAVIGATION,
       "Button Analyzer must own only PC1 and preserve existing tool IDs")
for operation in ("start", "poll", "stop", "reset", "change_quiet"):
    name = f"labmate_button_capture_{operation}"
    expect(len(re.findall(rf"(?m)^void\s+{name}\s*\(", BUTTON)) == 1
           and f"void {name}(LabMateApp* app" in BUTTON_H
           and f"{name}(app" in MAIN,
           f"Button capture missing lifecycle method {name}")
expect("GpioModeInterruptRiseFall" in BUTTON and "GpioPullUp" in BUTTON
       and "labmate_capture_can_start(app, LabMateCaptureButton)" in BUTTON
       and "labmate_capture_exti_clear(" in BUTTON
       and "furi_hal_gpio_remove_int_callback(" in BUTTON
       and "GpioModeAnalog" in BUTTON
       and "app->capture_owner = LabMateCaptureButton;" in BUTTON,
       "Button EXTI setup/teardown must remain PC1-only and exclusive")
expect("LL_EXTI_" not in BUTTON and "FURI_CRITICAL_ENTER()" in BUTTON
       and "FURI_CRITICAL_EXIT()" in BUTTON
       and "labmate_button_edge(" in BUTTON
       and "labmate_button_poll(" in BUTTON
       and "labmate_button_snapshot(" in BUTTON,
       "Button ISR must publish raw edges; app thread must validate snapshot atomically")
expect("labmate_button_state_init(" in BUTTON_LOGIC
       and "labmate_button_poll(" in BUTTON_LOGIC
       and "labmate_button_snapshot(" in BUTTON_LOGIC
       and "storage_" not in BUTTON_LOGIC
       and "furi_" not in BUTTON_LOGIC,
       "Portable contact logic must be isolated from firmware, GPIO and SD")
expect("case LabMateScreenButton:" in MAIN
       and "case LabMateToolButton:" in MAIN
       and "labmate_button_capture_stop(app);" in MAIN
       and "button_quiet_ms;" in INTERNAL_H
       and '"BUTTON"' in SCREENS
       and "app->button_details_view" in SCREENS
       and "app->button_details_view = !app->button_details_view;" in MAIN
       and '"SET:"' not in SCREENS,  # Screen must label physical settling, not reaction time.
       "Button Analyzer must expose state, settling and BACK cleanup")
expect((ROOT / "tests/test_button_logic.c.inc").is_file()
       and not (ROOT / "tests/test_button_logic.c").exists(),
       "Button logic host-native tests must never link into FAP")

# Threshold Alerts never claim a peripheral, touch storage, or read ISR state
# from Canvas. One latched visual threshold can monitor a live instrument.
expect("LabMateToolAlerts" in (SRC / "labmate_navigation.h").read_text(encoding="utf-8")
       and '"Threshold Alerts"' in NAVIGATION
       and "case LabMateToolAlerts:" in MAIN
       and "case LabMateScreenAlerts:" in MAIN,
       "Threshold Alerts must have a menu entry and passive configuration screen")
expect("LabMateThreshold threshold;" in INTERNAL_H
       and "labmate_threshold_init(&app->threshold)" in MAIN
       and "threshold_update_from_measurement(app);" in MAIN
       and "app->threshold.latched" in SCREENS
       and "app->threshold.source == LabMateAlertFrequency" in SCREENS
       and "app->threshold.source == LabMateAlertPulseDuty" in SCREENS
       and "app->threshold.source == LabMateAlertCounter" in SCREENS
       and "app->threshold.source == LabMateAlertButtonSettle" in SCREENS,
       "Live threshold monitoring and on-instrument visual banner must be wired")
for operation in ("init", "change_source", "change_limit", "toggle", "acknowledge", "update"):
    fn = f"labmate_threshold_{operation}"
    expect(fn + "(" in THRESHOLD and fn + "(" in THRESHOLD_H,
           f"Missing portable alert operation {fn}")
expect("!app->hold" in ALERT_BRIDGE
       and "app->frequency_valid" in ALERT_BRIDGE
       and "app->pulse_period_valid" in ALERT_BRIDGE
       and "app->counter_active" in ALERT_BRIDGE
       and "app->button_active" in ALERT_BRIDGE
       and "app->frequency_millihz / 1000U" in ALERT_BRIDGE
       and "app->pulse_duty_permille / 10U" in ALERT_BRIDGE,
       "Alert samples must be gated and converted to user-visible units")
expect("storage_" not in THRESHOLD and "furi_" not in THRESHOLD
       and "labmate_threshold_update(" not in SCREENS
       and "labmate_threshold_change_limit(" not in SCREENS
       and "draw_alerts(" in SCREENS
       and '"ALERT LATCHED"' in SCREENS
       and '"WAITING FOR INPUT"' in SCREENS,
       "Threshold evaluation must be host-testable and the display passive")
expect((ROOT / "tests/test_threshold.c.inc").is_file()
       and not (ROOT / "tests/test_threshold.c").exists(),
       "Threshold tests must not be compiled into FAP")

PWM_SETTINGS = (SRC / "labmate_pwm_settings.c").read_text(encoding="utf-8")
PWM_SETTINGS_H = (SRC / "labmate_pwm_settings.h").read_text(encoding="utf-8")
expect("LABMATE_PWM_MAX_HZ 50000U" in PWM_SETTINGS_H
       and "LABMATE_PWM_MIN_HZ 1U" in PWM_SETTINGS_H
       and "LABMATE_PWM_MIN_DUTY 5U" in PWM_SETTINGS_H
       and "LABMATE_PWM_MAX_DUTY 95U" in PWM_SETTINGS_H,
       "PWM Studio safety limits missing")
expect("labmate_pwm_settings_valid(" in PWM_SETTINGS
       and "labmate_pwm_adjust_duty(" in PWM_SETTINGS
       and "labmate_pwm_adjust_hz(" in PWM_SETTINGS
       and "labmate_pwm_settings_valid(hz, app->generator_duty_percent)" in GENERATOR,
       "PWM output must use portable validated frequency/duty settings")
expect("labmate_generator_change_duty(app" in MAIN
       and "labmate_generator_begin_custom_edit(app)" in MAIN
       and "labmate_generator_finish_custom_edit(app, false)" in MAIN
       and "labmate_generator_finish_custom_edit(app, true)" in MAIN,
       "PWM Studio controls or custom edit commit/cancel missing")
expect("app->generator_running || app->generator_editing" in GENERATOR
       and "if(!app->generator_editing || app->generator_running) return;" in GENERATOR,
       "Custom editing must refuse running PWM")
expect("InputTypeShort" in MAIN and "InputTypeLong" in MAIN
       and "app->generator_skip_entry_ok" in MAIN
       and "app->generator_skip_entry_ok = true;" in MAIN,
       "Long-OK edit must not start PWM or consume menu OK release")
expect("labmate_generator_frequency(app)" in SCREENS
       and "app->generator_duty_percent" in SCREENS
       and '"EDIT CUSTOM"' in SCREENS,
       "PWM Studio must show custom Hz, duty and edit state")
expect(re.search(r"app->generator_freq_index\s*>=\s*LABMATE_PROFILE_GENERATOR_PRESETS", MAIN)
       and "app->profile_notice = 7U;" in MAIN,
       "Legacy profile records must reject unsupported custom frequency")
expect((ROOT / "tests/test_pwm_settings.c.inc").is_file()
       and not (ROOT / "tests/test_pwm_settings.c").exists(),
       "PWM Studio native tests must not become FAP translation units")

# The PB3/TIM2 hardware layer and EXTI trigger lifecycle now live in
# dedicated modules. Exclusive capture ownership still belongs to the app.
for fn in ("configure", "enable", "read", "shutdown"):
    name = f"labmate_frequency_tim2_{fn}"
    expect(len(re.findall(rf"(?m)^(?:void|uint32_t)\s+{name}\s*\(", TIM2_CAPTURE)) == 1,
           f"TIM2 driver missing exactly one {name} implementation")
    expect(f"{name}(void);" in TIM2_CAPTURE_H,
           f"TIM2 driver header missing {name}")
    expect(f"{name}(" in (MEASUREMENTS if fn == "read" else FREQ_CAPTURE),
           f"TIM2 driver is not called by expected owner: {name}")
expect("LL_TIM_" not in MAIN and "furi_hal_bus_" not in MAIN,
       "TIM2 LL and bus handling must stay out of labmate.c")
for fragment in ("GpioAltFn1TIM2", "LL_TIM_CLOCKSOURCE_EXT_MODE1",
                 "LL_TIM_IC_POLARITY_RISING", "FuriHalBusTIM2",
                 "LL_TIM_DisableCounter(", "GpioModeAnalog"):
    expect(fragment in TIM2_CAPTURE,
           f"TIM2 driver lost the tested hardware setting: {fragment}")
expect("labmate_capture_exti_clear(" in EXTI_CAPTURE_H
       and "labmate_capture_exti_clear(" in EXTI_CAPTURE,
       "Common EXTI release helper missing")
expect("FURI_CRITICAL_ENTER()" in EXTI_CAPTURE
       and "FURI_CRITICAL_EXIT()" in EXTI_CAPTURE
       and "LL_EXTI_DisableRisingTrig_0_31(line)" in EXTI_CAPTURE
       and "LL_EXTI_DisableFallingTrig_0_31(line)" in EXTI_CAPTURE
       and "LL_EXTI_ClearFlag_0_31(line)" in EXTI_CAPTURE,
       "EXTI trigger release must retain tested critical-section sequence")
expect("LL_EXTI_Disable" not in MAIN and "LL_EXTI_ClearFlag" not in MAIN
       and FREQ_CAPTURE.count("labmate_capture_exti_clear(") == 1
       and PULSE_CAPTURE.count("labmate_capture_exti_clear(") == 1,
       "LOW/PC1 pre-arm and Pulse stop must use common EXTI cleanup")

HISTORY = (SRC / "labmate_history.c").read_text(encoding="utf-8")
HISTORY_H = (SRC / "labmate_history.h").read_text(encoding="utf-8")
STORAGE_PATHS = (SRC / "labmate_storage_paths.h").read_text(encoding="utf-8")
for fn in ("scan", "open", "read_step", "close"):
    name = f"labmate_history_{fn}"
    expect(
        len(re.findall(rf"(?m)^void\s+{name}\s*\(", HISTORY)) == 1 and
        f"void {name}(LabMateApp* app);" in HISTORY_H and
        f"{name}(app)" in MAIN and
        not re.search(rf"(?m)^static void\s+history_{fn}\s*\(", MAIN),
        f"History {fn} must have exactly one implementation in history module",
    )
expect(
    "storage_file_write(" not in HISTORY and
    "storage_file_remove(" not in HISTORY and
    "storage_file_open(file, path, FSAM_READ, FSOM_OPEN_EXISTING)" in HISTORY and
    "LOGGER_HISTORY_READ_BYTES 256U" in HISTORY,
    "History CSV opens must remain read-only with bounded 256-byte reads",
)
expect(
    "bool labmate_history_delete_file(uint16_t log_id);" in HISTORY_H and
    len(re.findall(r"(?m)^bool\s+labmate_history_delete_file\s*\(", HISTORY)) == 1 and
    "log_id == 0U || log_id > 9999U" in HISTORY and
    "labmate_logger_filename_id(filename, &checked)" in HISTORY and
    'snprintf(path, sizeof(path), LOGGER_DIR "/%s", filename);' in HISTORY and
    "storage_common_remove(storage, path) == FSE_OK" in HISTORY and
    "storage_file_exists(storage, path)" in HISTORY and
    "storage_simply_remove_recursive" not in HISTORY and
    "labmate_history_delete_file(work->history_delete_id)" in MAIN and
    "work->history_delete_requested = true;" in MAIN and
    "app->history_delete_confirm = true;" in MAIN and
    "history_delete_target" not in MAIN and
    "app->history_delete_mode = !app->history_delete_mode;" in MAIN and
    "app->history_selected < app->history_count" in MAIN and
    "app->logger_file || app->logger_storage" in MAIN and
    "app->history_file || app->history_storage" in MAIN,
    "History removal must be explicitly confirmed, single-ID bounded and deferred",
)
expect(
    '#define LABMATE_LOGGER_DIR "/ext/apps_data/labmate"' in STORAGE_PATHS and
    '#define LOGGER_DIR LABMATE_LOGGER_DIR' in LOGGER_STORAGE and
    '#define LOGGER_DIR LABMATE_LOGGER_DIR' in HISTORY,
    "Storage path must stay shared and compatible with older CSV logs",
)
PULSE_MATH = (SRC / "labmate_pulse_math.c").read_text(encoding="utf-8")
PULSE_MATH_H = (SRC / "labmate_pulse_math.h").read_text(encoding="utf-8")
expect(
    "labmate_pulse_period_and_duty(" in MEASUREMENTS and
    "labmate_pulse_median5(" in MEASUREMENTS and
    "static uint32_t pulse_stats_median5(" not in MAIN and
    "labmate_pulse_period_and_duty(" in PULSE_MATH and
    "labmate_pulse_median5(" in PULSE_MATH and
    "labmate_pulse_period_and_duty(" in PULSE_MATH_H and
    "labmate_pulse_median5(" in PULSE_MATH_H,
    "Pulse period/duty and median-of-five must be split into portable math module",
)
expect(
    "#define PULSE_STATS_FILTER_SAMPLES LABMATE_PULSE_MEDIAN_SAMPLES" in INTERNAL_H and
    "#define LABMATE_PULSE_MEDIAN_SAMPLES 5U" in PULSE_MATH_H and
    "furi_" not in PULSE_MATH and "LL_TIM_" not in PULSE_MATH and
    "storage_" not in PULSE_MATH,
    "Pulse math must preserve five-value filter and avoid SDK/SD/hardware calls",
)
expect(
    "void labmate_logger_storage_stop(LabMateApp* app)" in LOGGER_STORAGE and
    "bool labmate_logger_storage_start(LabMateApp* app)" in LOGGER_STORAGE and
    "void labmate_logger_storage_stop(LabMateApp* app);" in LOGGER_STORAGE_H and
    "bool labmate_logger_storage_start(LabMateApp* app);" in LOGGER_STORAGE_H and
    "labmate_logger_storage_stop(app)" in MAIN and
    "labmate_logger_storage_start(app)" in MAIN and
    "static void logger_stop(" not in MAIN and
    "static bool logger_start(" not in MAIN,
    "CSV file lifecycle must have one implementation in its storage module",
)
expect(
    "storage_file_write(app->logger_file, header, header_size)" in LOGGER_STORAGE and
    "storage_file_open(" in LOGGER_STORAGE and
    "FSOM_CREATE_NEW" in LOGGER_STORAGE and
    "storage_file_sync(app->logger_file)" in LOGGER_STORAGE and
    "storage_file_close(app->logger_file)" in LOGGER_STORAGE and
    "labmate_logger_filename_id(" in LOGGER_STORAGE and
    '#define LOGGER_DIR LABMATE_LOGGER_DIR' in LOGGER_STORAGE,
    "CSV storage must retain exclusive file creation, flush, close and naming",
)
expect(
    "logger_prepare_row(" in MAIN and
    "labmate_capture_stop_all(" in MAIN and
    "labmate_logger_storage_start(" not in SCREENS and
    "labmate_logger_storage_stop(" not in SCREENS,
    "CSV app capture and drawing must remain separate from SD I/O",
)
expect('"v1.8dev"' in INTERNAL_H, "v1.8 dev LCD label required")
expect('fap_version="1.8"' in MANIFEST, "v1.8 dev manifest version required")
expect(
    'sources=["src/*.c"]' in MANIFEST,
    "FAP source list must explicitly exclude native C test fixtures",
)
expect(
    (ROOT / "tests/test_resource_policy.c.inc").is_file()
    and not (ROOT / "tests/test_resource_policy.c").exists(),
    "Native PA7 tests must not be included as a FAP .c translation unit",
)
expect('"3.3V GPIO ONLY"' in SCREENS, "Safety indication missing from About screen")

# Stable candidate measurement extraction must retain exactly one aggregation
# implementation, with app core only calling the new typed service API.
for name in ("measurement_reset", "frequency_stats_reset", "pulse_stats_reset", "pulse_stats_window_reset", "measurement_update"):
    expect(
        len(re.findall(rf"(?m)^void\s+{name}\s*\(", MEASUREMENTS)) == 1
        and f"void {name}(LabMateApp* app);" in MEASUREMENTS_H
        and f"{name}(app)" in MAIN
        and re.search(rf"(?m)^(?:static\s+)?void\s+{name}\s*\(", MAIN) is None,
        f"Measurement aggregator {name} must be in labmate_measurements.c only",
    )
expect("storage_" not in MEASUREMENTS and "furi_hal_pwm_" not in MEASUREMENTS,
       "Measurement aggregation must never write SD or own PWM hardware")

# Sample-formatting and alert validity remain app-thread only after extraction.
expect("bool logger_prepare_row(LabMateApp* app, char* row, size_t capacity)" in LOGGER_SNAPSHOT
       and "bool logger_prepare_row(LabMateApp* app, char* row, size_t capacity);" in LOGGER_SNAPSHOT_H
       and "logger_prepare_row(app, work->pending_log_row, sizeof(work->pending_log_row))" in MAIN
       and "labmate_logger_format_row(" in LOGGER_SNAPSHOT
       and "storage_" not in LOGGER_SNAPSHOT and "furi_hal_" not in LOGGER_SNAPSHOT,
       "CSV snapshots must be pure app-thread data sampling, without SD or GPIO calls")
expect("void threshold_update_from_measurement(LabMateApp* app)" in ALERT_BRIDGE
       and "void threshold_update_from_measurement(LabMateApp* app);" in ALERT_BRIDGE_H
       and "threshold_update_from_measurement(app);" in MAIN
       and "labmate_threshold_update(&app->threshold, valid, sample)" in ALERT_BRIDGE
       and "storage_" not in ALERT_BRIDGE and "furi_hal_" not in ALERT_BRIDGE,
       "Threshold sample validity adapter must have no hardware/storage side-effects")

# A background TIM1 PWM output owns PA7. The GPIO Monitor must not
# reconfigure that pin (including on entry with a stale PA7 selection).
expect(
    "labmate_monitor_entry_pin(app->gpio_index, app->generator_running)" in MONITOR_GPIO,
    "GPIO Monitor entry must respect background PA7 ownership",
)
expect(
    "labmate_monitor_next_pin(app->gpio_index, direction, app->generator_running)" in MAIN,
    "GPIO Monitor navigation must skip reserved PA7",
)
expect(
    "labmate_monitor_pin_allowed(index, app->generator_running)" in MONITOR_GPIO,
    "GPIO release must not reconfigure a reserved PA7 PWM output",
)
expect(
    "void labmate_monitor_gpio_release(LabMateApp* app, uint8_t index)" in MONITOR_GPIO,
    "GPIO release must receive app ownership context",
)
expect("furi_hal_gpio_read(" not in MAIN and
       "furi_hal_gpio_init_simple(" not in MAIN and
       "labmate_monitor_gpio_activate(app)" in MAIN and
       "labmate_monitor_gpio_release(app" in MAIN and
       "labmate_monitor_gpio_read(app->gpio_index)" in MAIN,
       "GPIO polling/release operations must be delegated from app")
for name in ("activate", "release", "read"):
    expect(f"labmate_monitor_gpio_{name}(" in MONITOR_GPIO and
           f"labmate_monitor_gpio_{name}(" in MONITOR_GPIO_H,
           f"GPIO Monitor driver missing {name}")
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


expect(
    "labmate_nav_tool_at(app->menu_group, app->selected)" in MAIN
    and "labmate_nav_group_size(app->menu_group)" in MAIN
    and "labmate_nav_group_size(app->menu_group)" in SCREENS,
    "Navigation input and renderer must use one shared grouping policy",
)
expect(
    '"GPIO Monitor"' in NAVIGATION and '"Log History"' in NAVIGATION
    and '"About"' in NAVIGATION and "menu_in_group" in INTERNAL_H,
    "All seven existing instruments must remain reachable through the menu",
)


# Saved-profile serialization is pure/host-testable and intentionally has no
# direct storage, IRQ, timer or GPIO access; file persistence comes later.
expect(
    "labmate_profiles_decode(" in PROFILES and
    "labmate_profiles_encode(" in PROFILES and
    "labmate_profiles_is_newer(" in PROFILES,
    "Missing portable profile codec functions",
)
expect(
    re.search(r"\bstorage_\w+\s*\(", PROFILES) is None and
    re.search(r"\bfuri_hal_\w+\s*\(", PROFILES) is None,
    "Profile codec must stay independent from storage and hardware",
)

# A one-edge 100 ms counter bin must not generate a misleading 10 Hz
# sample for a 1 Hz source. Hardware polling and sample gates are separate.
expect(
    "labmate_high_gate_evaluate(" in MEASUREMENTS and
    "frequency_hw_last_poll_count" in MEASUREMENTS and
    "frequency_hw_last_poll_cycle" in MEASUREMENTS and
    "frequency_hw_gate_started" in MEASUREMENTS and
    "LabMateHighGatePublish" in MEASUREMENTS,
    "PB3 high-frequency meter must use the adaptive sample gate",
)
expect(
    "LABMATE_HIGH_GATE_MIN_EDGES" in FREQUENCY_GATE and
    "LABMATE_HIGH_GATE_SLOW_SECONDS" in FREQUENCY_GATE and
    "LL_TIM_" not in FREQUENCY_GATE and
    "furi_hal_" not in FREQUENCY_GATE,
    "Adaptive gate must be pure host-testable estimation logic",
)

# New Profiles tool is appended; original seven instruments retain IDs.
expect(
    '"Profiles"' in NAVIGATION and
    "case LabMateToolProfiles:" in MAIN and
    "void draw_profiles(" in SCREENS and
    "labmate_profile_sd_load(" in MAIN and
    "labmate_profile_sd_save(" in MAIN,
    "Missing profile navigation, UI or deferred microSD I/O",
)
expect(
    "app->profile_confirm = true;" in MAIN and
    "work->profiles_delete_requested = app->profile_action == 2U;" in MAIN and
    "memset(profile, 0, sizeof(*profile));" in MAIN and
    'app->profile_action == 2U ? "DELETE" : "SAVE"' in SCREENS and
    'ui_footer_pair(canvas, "OK",' in SCREENS and
    '"BACK", "NO"' in SCREENS and
    "app->preferred_frequency_pin = profile->frequency_pin;" in MAIN and
    "app->preferred_pulse_pin = profile->pulse_pin;" in MAIN and
    "app->generator_running ||" in MAIN,
    "Profile save must confirm and load must refuse an active generator",
)
expect(
    "profiles_read_requested" in MAIN and
    "profiles_save_requested" in MAIN and
    "labmate_profiles_decode(" in PROFILES,
    "Profile I/O needs deferred main-thread work and verified codec",
)

LOGGER_CODEC = (SRC / "labmate_logger_codec.c").read_text(encoding="utf-8")
LOGGER_HEADER = (SRC / "labmate_logger_codec.h").read_text(encoding="utf-8")
expect(
    '"labmate_logger_codec.h"' in LOGGER_SNAPSHOT and
    "labmate_logger_filename_id(" in LOGGER_STORAGE and
    "labmate_logger_format_row(" in LOGGER_SNAPSHOT and
    "static bool logger_filename_id(" not in MAIN,
    "Missing extracted logger codec calls",
)
expect(
    "bool labmate_logger_filename_id(" in LOGGER_CODEC and
    "int labmate_logger_format_row(" in LOGGER_CODEC and
    "int labmate_logger_format_row(" in LOGGER_HEADER and
    "storage_" not in LOGGER_CODEC and "furi_" not in LOGGER_CODEC,
    "Logger codec must be hardware/storage independent",
)

if failures:
    for error in failures:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print(f"LabMate v1.6 boundaries OK: {len(SCREENS_EXPECTED)} view-only screens")
print("GPIO IRQ and PWM retained in core; history and logger storage modules extracted")
print("NOTE: static checks cannot verify behavior on the physical Flipper")

# v1.8 coordinator responsibility gates: smaller entry point, single
# dispatch owner, passive rendering, bounded deferred samples and one
# shared capture teardown path. Never silently regress the monolith.
expect(len(COORDINATOR.splitlines()) < 250,
       "v1.8 coordinator must stay below 250 lines")
expect("void labmate_input_dispatch(" in INPUT_DISPATCH
       and "labmate_input_dispatch(app, status, event, &work);" in COORDINATOR
       and "case LabMateToolGenerator:" in SCREEN_HANDLERS,
       "Input event dispatch must be owned only by input module")
expect(len(INPUT_DISPATCH.splitlines()) <= 80
       and "switch(app->screen)" in INPUT_DISPATCH
       and "labmate_input_generator(app, event, work);" in INPUT_DISPATCH
       and "labmate_input_profiles(app, event, work);" in INPUT_DISPATCH,
       "Input dispatcher must only route events to dedicated screen handlers")
expect("void labmate_capture_stop_all(" in CAPTURE_SESSION
       and "labmate_capture_stop_all(app);" in COORDINATOR
       and "furi_hal_pwm_" not in CAPTURE_SESSION,
       "Capture teardown ownership and independent PWM isolation broken")
expect("void labmate_deferred_prepare(" in DEFERRED_IO
       and "void labmate_deferred_execute(" in DEFERRED_IO
       and "labmate_deferred_prepare(app, &work);" in COORDINATOR
       and "furi_mutex_release(app->mutex);\n\n        labmate_deferred_execute(" in COORDINATOR
       and "storage_file_write(app->logger_file," in DEFERRED_IO
       and "storage_file_write(" not in COORDINATOR,
       "SD work must remain deferred until after UI mutex release")
expect("void labmate_view_render_callback(" in VIEW_COORDINATOR
       and "view_port_update(viewport)" in VIEW_COORDINATOR
       and "storage_file_" not in VIEW_COORDINATOR
       and "furi_hal_gpio_" not in VIEW_COORDINATOR,
       "GUI module must remain passive and avoid direct hardware/SD IO")
