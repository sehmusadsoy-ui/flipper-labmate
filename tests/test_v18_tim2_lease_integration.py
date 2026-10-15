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
extern bool lease_available, release_succeeds;
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
#define furi_hal_bus_enable(...) (++hw_writes)
#define furi_hal_bus_disable(...) (++hw_writes)
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
bool lease_available, release_succeeds = true;
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
    labmate_frequency_tim2_enable();
    labmate_frequency_tim2_disable();
    assert(labmate_frequency_tim2_read() == 0U);
    labmate_frequency_tim2_shutdown();
    assert(hw_writes == 0 && hw_reads == 0 && lease_releases == 0);
#ifdef HAS_LEASE
    assert(lease_attempts == 1);
    lease_available = true;
    assert(labmate_frequency_tim2_configure());
    assert(hw_writes > 0);
    int before = hw_writes;
    assert(!labmate_frequency_tim2_configure()); /* no double claim */
    assert(hw_writes == before && lease_attempts == 2);
    labmate_frequency_tim2_enable();
    assert(labmate_frequency_tim2_read() == 23U);
    labmate_frequency_tim2_disable();
    assert(hw_reads == 1);
    labmate_frequency_tim2_shutdown();
    assert(lease_releases == 1);
    before = hw_writes;
    labmate_frequency_tim2_shutdown();
    labmate_frequency_tim2_disable();
    labmate_frequency_tim2_enable();
    assert(hw_writes == before && hw_reads == 1);
    /* Failed release blocks all future configuration and double teardown. */
    release_succeeds = false;
    assert(labmate_frequency_tim2_configure());
    labmate_frequency_tim2_shutdown();
    assert(lease_releases == 2);
    before = hw_writes;
    assert(!labmate_frequency_tim2_configure());
    labmate_frequency_tim2_shutdown();
    assert(hw_writes == before && lease_releases == 2);
#else
    assert(lease_attempts == 0);
    lease_available = true;
    assert(!labmate_frequency_tim2_configure());
    assert(hw_writes == 0 && lease_releases == 0);
#endif
    return 0;
}
"""


def test_one(has_lease: bool) -> None:
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
        args.extend([str(root / "harness.c"), "-o", str(exe)])
        subprocess.run(args, check=True)
        subprocess.run([str(exe)], check=True)


def test_callers() -> None:
    for path in ("src/labmate_frequency_capture.c", "src/labmate_event_counter.c"):
        content = (ROOT / path).read_text()
        required = (
            "if(!labmate_frequency_tim2_configure()) {\n"
            "        app->capture_blocked = true;\n"
            "        return;\n"
            "    }"
        )
        assert required in content, f"missing failure handling: {path}"
        start_name = "labmate_frequency_high_start" if "frequency_capture" in path else "labmate_event_counter_start"
        start = content.index("void " + start_name + "(")
        remainder = content[start:]
        assert remainder.index(required) < remainder.index("app->capture_owner ="), path
    assert "bool labmate_frequency_tim2_configure(void);" in HEADER.read_text()


if __name__ == "__main__":
    test_callers()
    test_one(False)
    test_one(True)
    print("E11.1d ACTUAL PB3/TIM2 DRIVER HOST PASS: failed claim has ZERO HAL writes,")
    print("no stale cleanup; acquired lifecycle, STOP/lease release, and fail closed.")
    print("NOT firmware-global ownership, physical timer validation or device PASS.")
