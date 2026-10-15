#!/usr/bin/env python3
"""E11.1e: compile and execute the actual PWM generator production C driver.

Mock HAL records TIM1/PA7 calls; old SDK and denied firmware-lease paths
MUST have zero peripheral mutations. This is HOST CI, not STM32 evidence.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/labmate_generator.c"

MOCK = r"""
#ifndef E11_PWM_MOCK_H
#define E11_PWM_MOCK_H
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#define LABMATE_PWM_CUSTOM_INDEX 15U
#define LABMATE_PWM_PRESET_COUNT 15U
#define FuriHalPwmOutputIdTim1PA7 7
#ifdef HAS_LEASE
#define FURI_HAL_RESOURCE_LEASE_API_V1 1
#define FURI_HAL_LEASE_PWM_PA7 3U
#endif
typedef struct {
    bool generator_running, generator_state, generator_editing;
    bool generator_blocked, generator_release_fault;
    uint8_t generator_freq_index, generator_duty_percent;
    uint32_t generator_custom_hz, generator_custom_draft_hz;
    uint8_t generator_custom_step_index, generator_edit_original_index;
} LabMateApp;
extern unsigned pwm_start_calls, pwm_stop_calls, pwm_update_calls;
extern unsigned lease_attempts, lease_releases;
extern bool lease_available, release_succeeds;
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask);
bool furi_hal_resource_lease_release(uint32_t handle, uint32_t mask);
bool labmate_pwm_settings_valid(uint32_t hz, uint8_t duty);
uint8_t labmate_pwm_adjust_duty(uint8_t duty, int8_t dir);
uint32_t labmate_pwm_adjust_hz(uint32_t hz, int8_t dir, uint32_t step);
void furi_hal_pwm_start(int id, uint32_t hz, uint8_t duty);
void furi_hal_pwm_stop(int id);
void furi_hal_pwm_set_params(int id, uint32_t hz, uint8_t duty);
#endif
"""

HARNESS = r"""
#include <assert.h>
#include "mock.h"
unsigned pwm_start_calls, pwm_stop_calls, pwm_update_calls;
unsigned lease_attempts, lease_releases;
bool lease_available, release_succeeds = true;
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
    assert(mask==3U);
    lease_attempts++;
    return lease_available ? 77U : 0U;
}
bool furi_hal_resource_lease_release(uint32_t handle, uint32_t mask) {
    assert(handle==77U && mask==3U);
    assert(pwm_stop_calls>0U); /* releasing before stopping TIM1 is unsafe */
    lease_releases++;
    return release_succeeds;
}
bool labmate_pwm_settings_valid(uint32_t hz, uint8_t duty) {
    return hz>=1U && hz<=50000U && duty>=5U && duty<=95U;
}
uint8_t labmate_pwm_adjust_duty(uint8_t duty, int8_t dir) {
    return (uint8_t)(duty + (dir>0?1:-1));
}
uint32_t labmate_pwm_adjust_hz(uint32_t hz, int8_t dir, uint32_t step) {
    return dir>0 ? hz+step : hz-step;
}
void furi_hal_pwm_start(int id, uint32_t hz, uint8_t duty) {
    assert(id==7 && hz>0U && duty>0U);
    assert(lease_available);
    pwm_start_calls++;
}
void furi_hal_pwm_stop(int id) {
    assert(id==7 && pwm_start_calls>pwm_stop_calls);
    pwm_stop_calls++;
}
void furi_hal_pwm_set_params(int id, uint32_t hz, uint8_t duty) {
    assert(id==7 && hz>0U && duty>0U && lease_available);
    assert(pwm_start_calls>pwm_stop_calls);
    pwm_update_calls++;
}
#include "labmate_generator.c"
static unsigned hw_mutations(void) {
    return pwm_start_calls + pwm_stop_calls + pwm_update_calls;
}
int main(void) {
    LabMateApp app={.generator_freq_index=7U,.generator_duty_percent=50U,
                    .generator_custom_hz=1000U};
    /* An unmatched SDK or held lease must never call any PWM HAL. */
    labmate_generator_stop(&app);
    assert(hw_mutations()==0U);
    labmate_generator_start(&app);
    assert(!app.generator_running && app.generator_blocked);
    assert(hw_mutations()==0U && lease_releases==0U);
#ifdef HAS_LEASE
    assert(lease_attempts==1U);
    app.generator_blocked=false;
    lease_available=true;
    labmate_generator_start(&app);
    assert(app.generator_running && !app.generator_blocked);
    assert(pwm_start_calls==1U && lease_attempts==2U);
    unsigned before=hw_mutations(), claims=lease_attempts;
    labmate_generator_start(&app);
    assert(hw_mutations()==before && lease_attempts==claims);
    labmate_generator_change_frequency(&app,1);
    labmate_generator_change_duty(&app,1);
    assert(pwm_update_calls==2U);
    labmate_generator_stop(&app);
    assert(!app.generator_running && !app.generator_release_fault);
    assert(pwm_stop_calls==1U && lease_releases==1U);
    before=hw_mutations();
    labmate_generator_stop(&app);
    assert(hw_mutations()==before && lease_releases==1U);
    app.generator_blocked=false;
    release_succeeds=false;
    labmate_generator_start(&app);
    assert(app.generator_running);
    labmate_generator_stop(&app);
    assert(!app.generator_running && app.generator_release_fault);
    assert(app.generator_blocked && lease_releases==2U);
    before=hw_mutations(); claims=lease_attempts;
    labmate_generator_start(&app);
    labmate_generator_stop(&app);
    labmate_generator_change_frequency(&app,1);
    assert(hw_mutations()==before && lease_attempts==claims);
    assert(lease_releases==2U);
#else
    assert(lease_attempts==0U && lease_releases==0U);
    lease_available=true;
    app.generator_blocked=false;
    labmate_generator_start(&app);
    assert(!app.generator_running && app.generator_blocked);
    labmate_generator_change_frequency(&app,1);
    assert(hw_mutations()==0U && lease_attempts==0U);
#endif
    return 0;
}
"""

def one_test(has_lease: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="labmate_e11_pwm_") as folder:
        root = Path(folder)
        (root / "mock.h").write_text(MOCK)
        for name in ("labmate_generator.h", "furi_hal_pwm.h", "furi_hal_resources.h"):
            (root / name).write_text('#include "mock.h"\n')
        shutil.copy2(DRIVER, root / DRIVER.name)
        (root / "harness.c").write_text(HARNESS)
        binary = root / "test"
        command = [os.environ.get("CC", "cc"), "-std=c11", "-Wall", "-Wextra",
                   "-Werror", "-pedantic", "-O0", "-I", str(root)]
        if has_lease:
            command.append("-DHAS_LEASE=1")
        subprocess.run(command + [str(root / "harness.c"), "-o", str(binary)],
                       check=True)
        subprocess.run([str(binary)], check=True)

def guard_sources() -> None:
    src=DRIVER.read_text()
    assert src.index("furi_hal_resource_lease_try_acquire(") < src.index(
        "furi_hal_pwm_start("), "TIM1 acquisition must precede HAL writes"
    assert "furi_hal_resource_lease_release(" in src
    assert "app->generator_release_fault = true;" in src
    ui=(ROOT/"src/labmate_ui_screens.c").read_text()
    assert 'app->generator_release_fault ? "ERR"' in ui
    assert 'app->generator_blocked ? "BUSY"' in ui
    state=(ROOT/"src/labmate_internal.h").read_text()
    assert "bool generator_release_fault;" in state
    assert "bool generator_blocked;" in state

if __name__ == "__main__":
    guard_sources()
    one_test(False)
    one_test(True)
    print("E11.1e ACTUAL PWM TIM1/PA7 C HOST PASS:")
    print("stock SDK and BUSY acquisition zero hardware calls; retained lease")
    print("permits start/retune/stop, failure blocks restart, no double release.")
    print("NO mandatory Momentum service ownership or physical device PASS.")
