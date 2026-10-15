#!/usr/bin/env python3
"""E11.1d PC1/EXTI1: compile the actual LOW-frequency start/stop C bodies
against instrumented HAL mocks. CI host only; NO hardware/DFU/FAP install.
"""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/labmate_frequency_capture.c"

def extract_function(text: str, name: str) -> str:
    prefix = "void " + name + "(LabMateApp* app) {"
    pos = text.index(prefix)
    first = text.index("{", pos)
    depth = 0
    for idx in range(first, len(text)):
        if text[idx] == "{":
            depth += 1
        elif text[idx] == "}":
            depth -= 1
            if depth == 0:
                return text[pos:idx + 1]
    raise AssertionError("missing closing brace: " + name)

PRELUDE = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#define GPIO_COUNT 8
#define LL_EXTI_LINE_1 2U
#define GpioModeAnalog 0
#define GpioModeInterruptRise 1
#define GpioPullNo 0
#define GpioSpeedVeryHigh 3
#define FURI_HAL_LEASE_IRQ_PC1 0xC0U
#ifdef TEST_APIS
#define FURI_HAL_RESOURCE_LEASE_API_V1 1
#define FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK 1
#endif
typedef struct { unsigned pin; } GpioPin;
typedef enum { LabMateCaptureNone, LabMateCaptureFrequencyLow } LabMateCaptureOwner;
typedef struct {
    bool frequency_irq_active, frequency_irq_new_period, capture_blocked;
    unsigned gpio_index, capture_pin_index;
    LabMateCaptureOwner capture_owner;
    uint32_t frequency_irq_last_cycle, frequency_irq_period_cycles;
    uint32_t frequency_irq_last_tick, frequency_irq_edges;
} LabMateApp;
static GpioPin pc1 = {1};
const GpioPin* labmate_gpio_pins[GPIO_COUNT] = {NULL, &pc1};
static unsigned gpio_mutations, exti_mutations, irq_mutations;
static unsigned try_add_attempts, lease_attempts, lease_releases;
static bool lease_available, callback_available, release_succeeds = true;
static void frequency_gpio_callback(void* ctx) {(void)ctx;}
static bool labmate_capture_can_start(LabMateApp* app, LabMateCaptureOwner expected) {
    return expected == LabMateCaptureFrequencyLow &&
        app->capture_owner == LabMateCaptureNone && !app->frequency_irq_active &&
        app->gpio_index == 1U;
}
#ifdef TEST_APIS
static LabMateCaptureOwner labmate_capture_owner_after_stop(
    LabMateCaptureOwner owner, LabMateCaptureOwner stopping) {
    return owner == stopping ? LabMateCaptureNone : owner;
}
static uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
    assert(mask == FURI_HAL_LEASE_IRQ_PC1);
    lease_attempts++;
    return lease_available ? 77U : 0U;
}
static bool furi_hal_resource_lease_release(uint32_t handle, uint32_t mask) {
    assert(handle == 77U && mask == FURI_HAL_LEASE_IRQ_PC1);
    lease_releases++;
    return release_succeeds;
}
static bool furi_hal_gpio_try_add_int_callback(
    const GpioPin* pin, void (*cb)(void*), void* context) {
    assert(pin == &pc1 && cb && context);
    try_add_attempts++;
    if(!callback_available) return false;
    irq_mutations++; /* actual try-add enables EXTI IT on success only */
    return true;
}
static void labmate_capture_exti_clear(uint32_t line, bool rising) {
    assert(line == LL_EXTI_LINE_1);
    (void)rising;
    exti_mutations++;
}
#define furi_hal_gpio_init(...) (++gpio_mutations)
#define furi_hal_gpio_init_simple(...) (++gpio_mutations)
#define furi_hal_gpio_disable_int_callback(...) (++irq_mutations)
#define furi_hal_gpio_enable_int_callback(...) (++irq_mutations)
#define furi_hal_gpio_remove_int_callback(...) (++irq_mutations)
static uint32_t labmate_frequency_pc1_lease;
#endif
"""

TESTS = r"""
static unsigned hardware_mutations(void) {
    return gpio_mutations + exti_mutations + irq_mutations;
}
int main(void) {
    LabMateApp app = {.gpio_index=1, .capture_pin_index=GPIO_COUNT};
    /* Claim refusal, absent API and callback occupancy are side-effect free. */
    labmate_frequency_low_start(&app);
    assert(app.capture_blocked && !app.frequency_irq_active);
    assert(hardware_mutations()==0U && lease_releases==0U);
    labmate_frequency_low_stop(&app);
    assert(hardware_mutations()==0U && app.capture_pin_index==GPIO_COUNT);
#ifdef TEST_APIS
    assert(lease_attempts==1U && try_add_attempts==0U);
    app.capture_blocked=false;
    lease_available=true;
    callback_available=false; /* legacy owner occupies same EXTI line */
    labmate_frequency_low_start(&app);
    assert(app.capture_blocked && !app.frequency_irq_active);
    assert(hardware_mutations()==0U && try_add_attempts==1U);
    assert(lease_releases==1U && labmate_frequency_pc1_lease==0U);
    assert(app.capture_owner==LabMateCaptureNone && app.capture_pin_index==GPIO_COUNT);
    app.capture_blocked=false;
    callback_available=true;
    app.frequency_irq_edges=99U;
    labmate_frequency_low_start(&app);
    assert(app.frequency_irq_active && !app.capture_blocked);
    assert(app.capture_owner==LabMateCaptureFrequencyLow &&
           app.capture_pin_index==1U && app.frequency_irq_edges==0U);
    assert(labmate_frequency_pc1_lease==77U);
    assert(gpio_mutations==1U && exti_mutations==1U);
    unsigned old_hw=hardware_mutations(), old_claims=lease_attempts;
    labmate_frequency_low_start(&app);
    assert(hardware_mutations()==old_hw && lease_attempts==old_claims);
    labmate_frequency_low_stop(&app);
    assert(!app.frequency_irq_active && app.capture_owner==LabMateCaptureNone);
    assert(app.capture_pin_index==GPIO_COUNT && lease_releases==2U &&
           labmate_frequency_pc1_lease==0U);
    old_hw=hardware_mutations();
    labmate_frequency_low_stop(&app);
    assert(hardware_mutations()==old_hw && lease_releases==2U);
    /* Failure to release after teardown keeps handle and rejects next START. */
    release_succeeds=false;
    app.capture_blocked=false;
    labmate_frequency_low_start(&app);
    assert(app.frequency_irq_active);
    labmate_frequency_low_stop(&app);
    assert(!app.frequency_irq_active && app.capture_blocked);
    assert(labmate_frequency_pc1_lease==77U);
    old_hw=hardware_mutations();
    old_claims=lease_attempts;
    labmate_frequency_low_start(&app);
    assert(app.capture_blocked && !app.frequency_irq_active);
    assert(hardware_mutations()==old_hw && lease_attempts==old_claims);
#else
    assert(lease_attempts==0U && try_add_attempts==0U);
    lease_available=true;
    callback_available=true;
    app.capture_blocked=false;
    labmate_frequency_low_start(&app);
    assert(app.capture_blocked && hardware_mutations()==0U);
    assert(lease_attempts==0U && try_add_attempts==0U);
#endif
    return 0;
}
"""

def run(with_api: bool) -> None:
    src = SOURCE.read_text(encoding="utf-8")
    assert "if(!app->frequency_irq_active ||" in src, "early ISR guard missing"
    assert "app->capture_owner != LabMateCaptureFrequencyLow) return;" in src
    assert src.index("furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PC1)") < src.index(
        "furi_hal_gpio_try_add_int_callback(pin, frequency_gpio_callback, app)")
    low_start = extract_function(src, "labmate_frequency_low_start")
    low_stop = extract_function(src, "labmate_frequency_low_stop")
    assert low_start.index("furi_hal_gpio_try_add_int_callback") < low_start.index(
        "labmate_capture_exti_clear")
    full = PRELUDE + "\n" + low_start + "\n" + low_stop + "\n" + TESTS
    with tempfile.TemporaryDirectory(prefix="labmate_e11_pc1_") as d:
        folder = Path(d)
        p = folder / "harness.c"
        p.write_text(full, encoding="utf-8")
        binary = folder / "test"
        args = [os.environ.get("CC", "cc"), "-std=c11", "-Wall",
                "-Wextra", "-Werror", "-pedantic", "-O0"]
        if with_api:
            args.append("-DTEST_APIS=1")
        subprocess.run(args + [str(p), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)

if __name__ == "__main__":
    run(False)
    run(True)
    print("E11.1d PC1/EXTI1 EXACT production start/stop C HOST PASS:")
    print("missing API, denied lease, occupied callback ZERO HAL mutations;")
    print("success, STOP, duplicate calls, failed-release fail-closed.")
    print("NOT firmware-global owner coverage or physical device PASS.")
