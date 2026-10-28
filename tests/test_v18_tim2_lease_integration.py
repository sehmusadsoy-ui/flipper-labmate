#!/usr/bin/env python3
"""E11.1d: compile and execute the actual production PB3/TIM2 driver with
instrumented HAL stubs. No hardware, installation, or firmware flashing.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/labmate_frequency_tim2.c"
HEADER = ROOT / "src/labmate_frequency_tim2.h"

MOCK = r"""
#ifndef E11_TIM2_MOCK_H
#define E11_TIM2_MOCK_H
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
typedef struct { uint8_t pin; } GpioPin;
extern const GpioPin gpio_ext_pb3;
extern int hw_writes, hw_reads, lease_attempts, lease_releases;
extern bool lease_available, release_succeeds, bus_enabled;
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask);
bool furi_hal_resource_lease_release(uint32_t handle, uint32_t mask);
#ifdef HAS_LEASE
#define FURI_HAL_RESOURCE_LEASE_API_V1 1
#define FURI_HAL_LEASE_COUNTER_PB3 12U
#endif
#define GpioModeAltFunctionPushPull 1
#define GpioPullNo 0
#define GpioSpeedVeryHigh 3
#define GpioAltFn1TIM2 1
#define GpioModeAnalog 2
#define FuriHalBusTIM2 2
#define TIM2 ((void*)&hw_writes)
#define LL_TIM_COUNTERMODE_UP 0
#define LL_TIM_CLOCKDIVISION_DIV1 0
#define LL_TIM_CHANNEL_CH2 2
#define LL_TIM_ACTIVEINPUT_DIRECTTI 0
#define LL_TIM_ICPSC_DIV1 0
#define LL_TIM_IC_POLARITY_RISING 0
#define LL_TIM_IC_FILTER_FDIV1 0
#define LL_TIM_TS_TI2FP2 0
#define LL_TIM_CLOCKSOURCE_EXT_MODE1 0
typedef struct {
    uint32_t Prescaler, CounterMode, Autoreload, ClockDivision;
} LL_TIM_InitTypeDef;
static inline void e11_mock_tim_init(const LL_TIM_InitTypeDef* p) {
    (void)p;
    ++hw_writes;
}
#define furi_hal_gpio_init_ex(...) (++hw_writes)
#define furi_hal_gpio_init_simple(...) (++hw_writes)
static inline bool furi_hal_bus_is_enabled(int bus) {
    (void)bus;
    return bus_enabled;
}
static inline void e11_bus_enable(void) {
    ++hw_writes;
    bus_enabled = true;
}
static inline void e11_bus_disable(void) {
    ++hw_writes;
    bus_enabled = false;
}
#define furi_hal_bus_enable(...) e11_bus_enable()
#define furi_hal_bus_disable(...) e11_bus_disable()
#define LL_TIM_Init(t, cfg) e11_mock_tim_init(cfg)
#define LL_TIM_IC_SetActiveInput(...) (++hw_writes)
#define LL_TIM_IC_SetPrescaler(...) (++hw_writes)
#define LL_TIM_IC_SetPolarity(...) (++hw_writes)
#define LL_TIM_IC_SetFilter(...) (++hw_writes)
#define LL_TIM_SetTriggerInput(...) (++hw_writes)
#define LL_TIM_SetClockSource(...) (++hw_writes)
#define LL_TIM_CC_EnableChannel(...) (++hw_writes)
#define LL_TIM_SetCounter(...) (++hw_writes)
#define LL_TIM_EnableCounter(...) (++hw_writes)
#define LL_TIM_DisableCounter(...) (++hw_writes)
#define LL_TIM_CC_DisableChannel(...) (++hw_writes)
#define LL_TIM_GetCounter(...) (++hw_reads, 23U)
#endif
"""

HARNESS = r"""
#include <assert.h>
#include "mock.h"
int hw_writes, hw_reads, lease_attempts, lease_releases;
bool lease_available, release_succeeds = true, bus_enabled;
const GpioPin gpio_ext_pb3 = {3};
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
    assert(mask == 12U);
    ++lease_attempts;
    return lease_available ? 42U : 0U;
}
bool furi_hal_resource_lease_release(uint32_t handle, uint32_t mask) {
    assert(handle == 42U && mask == 12U);
    ++lease_releases;
    return release_succeeds;
}
#include "labmate_frequency_tim2.c"
int main(void) {
    /* Rejection must not change GPIO, IRQ, counter or clock registers. */
    assert(!labmate_frequency_tim2_configure());
    assert(!labmate_frequency_tim2_lease_pending());
    labmate_frequency_tim2_enable();
    labmate_frequency_tim2_disable();
    assert(labmate_frequency_tim2_read() == 0U);
    labmate_frequency_tim2_shutdown();
    assert(hw_writes == 0 && hw_reads == 0 && lease_releases == 0);
    assert(!labmate_frequency_tim2_capture_valid());
#ifdef HAS_LEASE
    assert(lease_attempts == 1);
#ifdef TEST_LEGACY_BUSY_RELEASE_FAULT
    /* A legacy timer is already running AND firmware refuses to release
     * our temporary claim. Even after the timer becomes idle, no retry,
     * teardown or hardware change is safe with that unresolved handle.
     */
    lease_available = true;
    bus_enabled = true;
    release_succeeds = false;
    {
        const int previous_writes = hw_writes;
        const int previous_reads = hw_reads;
        assert(!labmate_frequency_tim2_configure());
        assert(hw_writes == previous_writes && hw_reads == previous_reads);
        assert(lease_releases == 1);
        assert(labmate_frequency_tim2_lease_pending());
        bus_enabled = false;
        release_succeeds = true;
        assert(!labmate_frequency_tim2_configure());
        assert(!labmate_frequency_tim2_capture_valid());
        labmate_frequency_tim2_enable();
        labmate_frequency_tim2_disable();
        assert(labmate_frequency_tim2_read() == 0U);
        labmate_frequency_tim2_shutdown();
        assert(hw_writes == previous_writes && hw_reads == previous_reads);
        assert(lease_attempts == 2 && lease_releases == 1);
        assert(labmate_frequency_tim2_lease_pending());
    }
    return 0;
#endif
    lease_available = true;
    /* Legacy RFID/SubGHz owner enabled TIM2 but never opted in.
     * Must be detected before modifying PB3 or enabling timer twice.
     */
    bus_enabled = true;
    int before = hw_writes;
    assert(!labmate_frequency_tim2_configure());
    assert(hw_writes == before && lease_releases == 1);
    assert(!labmate_frequency_tim2_lease_pending());
    bus_enabled = false;
    assert(labmate_frequency_tim2_configure());
    assert(labmate_frequency_tim2_capture_valid());
    assert(labmate_frequency_tim2_lease_pending());
    assert(hw_writes > 0);
    before = hw_writes;
    assert(!labmate_frequency_tim2_configure()); /* no double claim */
    assert(hw_writes == before && lease_attempts == 3);
    labmate_frequency_tim2_enable();
    assert(labmate_frequency_tim2_read() == 23U);
    labmate_frequency_tim2_disable();
    assert(hw_reads == 1);
    labmate_frequency_tim2_shutdown();
    assert(lease_releases == 2);
    assert(!labmate_frequency_tim2_lease_pending());
    before = hw_writes;
    labmate_frequency_tim2_shutdown();
    labmate_frequency_tim2_disable();
    labmate_frequency_tim2_enable();
    assert(hw_writes == before && hw_reads == 1);
#ifdef TEST_LEGACY_CLOCK_LOSS
    /* A bypassing radio/RFID driver switched off the TIM2 clock.
     * Never read, disable or reset TIM2/PB3 from this point. Our lease
     * remains held until firmware reset to avoid a dangerous reuse.
     */
    assert(labmate_frequency_tim2_configure());
    bus_enabled = false;
    before = hw_writes;
    int read_before = hw_reads, release_before = lease_releases;
    assert(!labmate_frequency_tim2_capture_valid());
    labmate_frequency_tim2_enable();
    labmate_frequency_tim2_disable();
    assert(labmate_frequency_tim2_read() == 0U);
    labmate_frequency_tim2_shutdown();
    assert(hw_writes == before && hw_reads == read_before);
    assert(lease_releases == release_before);
    assert(labmate_frequency_tim2_lease_pending());
    bus_enabled = true; /* A foreign user restored the clock */
    assert(!labmate_frequency_tim2_capture_valid());
    assert(!labmate_frequency_tim2_configure());
    labmate_frequency_tim2_shutdown();
    assert(hw_writes == before && lease_releases == release_before);
#else
    /* Failed release blocks all future configuration and double teardown. */
    release_succeeds = false;
    assert(labmate_frequency_tim2_configure());
    labmate_frequency_tim2_shutdown();
    assert(lease_releases == 3);
    assert(labmate_frequency_tim2_lease_pending());
    before = hw_writes;
    assert(!labmate_frequency_tim2_configure());
    labmate_frequency_tim2_shutdown();
    assert(hw_writes == before && lease_releases == 3);
#endif
#else
    assert(lease_attempts == 0);
    lease_available = true;
    assert(!labmate_frequency_tim2_configure());
    assert(hw_writes == 0 && lease_releases == 0);
#endif
    return 0;
}
"""


def test_one(has_lease: bool, legacy_clock_loss: bool=False,
             legacy_busy_release_fault: bool=False) -> None:
    with tempfile.TemporaryDirectory(prefix="labmate_e11_tim2_") as tmp:
        root = Path(tmp)
        (root / "mock.h").write_text(MOCK)
        for name in (
            "furi_hal.h",
            "furi_hal_resources.h",
            "furi_hal_bus.h",
            "stm32wbxx_ll_tim.h",
        ):
            (root / name).write_text('#include "mock.h"\n')
        shutil.copy2(DRIVER, root / DRIVER.name)
        shutil.copy2(HEADER, root / HEADER.name)
        (root / "harness.c").write_text(HARNESS)
        exe = root / "driver_test"
        args = [
            os.environ.get("CC", "cc"),
            "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
            "-O0", "-I", str(root),
        ]
        if has_lease:
            args.append("-DHAS_LEASE=1")
        if legacy_clock_loss:
            args.append("-DTEST_LEGACY_CLOCK_LOSS=1")
        if legacy_busy_release_fault:
            args.append("-DTEST_LEGACY_BUSY_RELEASE_FAULT=1")
        args.extend([str(root / "harness.c"), "-o", str(exe)])
        subprocess.run(args, check=True)
        subprocess.run([str(exe)], check=True)


def test_callers() -> None:
    for path in ("src/labmate_frequency_capture.c", "src/labmate_event_counter.c"):
        content = (ROOT / path).read_text()
        required = (
            "if(!labmate_frequency_tim2_configure()) {\n"
            "        app->capture_blocked = true;\n"
            "        /* BUSY if a legacy native timer is already active; ERR if the\n"
            "         * fresh lease could not be released and must remain reserved.\n"
            "         */\n"
            "        if(labmate_frequency_tim2_lease_pending()) app->capture_release_fault = true;\n"
            "        return;\n"
            "    }"
        )
        assert required in content, f"missing failure handling: {path}"
        start_name = "labmate_frequency_high_start" if "frequency_capture" in path else "labmate_event_counter_start"
        start = content.index("void " + start_name + "(")
        remainder = content[start:]
        assert remainder.index(required) < remainder.index("app->capture_owner ="), path
    for path in ("src/labmate_frequency_capture.c", "src/labmate_event_counter.c"):
        # Current Counter STOP caches the one lease-pending read and checks
        # it immediately; legacy Frequency STOP checks the call directly.
        # Both must set sticky fault + blocked before returning ownership.
        source = (ROOT/path).read_text()
        if "if(labmate_frequency_tim2_lease_pending()) {" not in source:
            assert "const bool lease_pending = labmate_frequency_tim2_lease_pending();" in source, path
            assert "if(lease_pending) {" in source, path
            pending_block = source.split("if(lease_pending) {", 1)[1].split("}", 1)[0]
            assert "app->capture_release_fault = true;" in pending_block, path
            assert "app->capture_blocked = true;" in pending_block, path
    assert "bool labmate_frequency_tim2_configure(void);" in HEADER.read_text()
    assert "bool labmate_frequency_tim2_lease_pending(void);" in HEADER.read_text()
    assert "bool labmate_frequency_tim2_capture_valid(void);" in HEADER.read_text()
    counter=(ROOT/"src/labmate_event_counter.c").read_text()
    assert "if(!labmate_frequency_tim2_capture_valid())" in counter
    assert "if(healthy && app->capture_owner == LabMateCaptureCounter)" in counter
    high=(ROOT/"src/labmate_measurements.c").read_text()
    assert "if(!labmate_frequency_tim2_capture_valid())" in high


if __name__ == "__main__":
    test_callers()
    test_one(False)
    test_one(True)
    test_one(True,legacy_clock_loss=True)
    test_one(True,legacy_busy_release_fault=True)
    print("E11.1d ACTUAL PB3/TIM2 DRIVER HOST PASS: failed claim has ZERO HAL writes,")
    print("no stale cleanup; acquired lifecycle, STOP/lease release, and fail closed.")
    print("NOT firmware-global ownership, physical timer validation or device PASS.")
