#!/usr/bin/env python3
"""Real-code joint regression: actual native Momentum PWM C + LabMate generator C.

The two previously independent unit suites could both PASS while the FAP
preclaimed the same TIM1/PA7 lease the native PWM HAL attempts to claim.
Here both real C translation units execute in ONE mocked firmware process.
"""
from __future__ import annotations
from pathlib import Path
import importlib.util
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
NATIVE=ROOT/"tests/test_v18_native_pwm_lease.py"
GENERATOR=ROOT/"src/labmate_generator.c"

HEADER=r'''
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <assert.h>
#include <stddef.h>
typedef enum {
    FuriHalPwmOutputIdNone,FuriHalPwmOutputIdTim1PA7,
    FuriHalPwmOutputIdLptim2PA4
} FuriHalPwmOutputId;
typedef enum {FuriHalBusTIM1,FuriHalBusLPTIM2} FuriHalBus;
typedef struct {int pin;} GpioPin;
extern const GpioPin gpio_ext_pa7,gpio_ext_pa4;
extern unsigned mock_ll_writes;
#define FURI_HAL_LEASE_PWM_PA7 ((1U<<0)|(1U<<1))
#define FURI_HAL_LEASE_MONITOR_PA7 (1U<<1)
#define FURI_HAL_LEASE_MONITOR_PA4 (1U<<11)
#define FURI_HAL_LEASE_ONEWIRE_PA4 (1U<<11)
#define FURI_HAL_RESOURCE_LEASE_API_V1 1
#define FURI_HAL_PWM_NATIVE_LEASE_API_V1 1
#define GpioModeAltFunctionPushPull 1
#define GpioModeAnalog 2
#define GpioPullNo 0
#define GpioSpeedVeryHigh 3
#define GpioAltFn1TIM1 1
#define GpioAltFn14LPTIM2 14
#define TIM1 1
#define LPTIM2 2
#define furi_crash() abort()
#define furi_assert(x) assert(x)
void furi_hal_gpio_init_ex(const GpioPin*,int,int,int,int);
void furi_hal_gpio_init_simple(const GpioPin*,int);
bool furi_hal_bus_is_enabled(FuriHalBus);
void furi_hal_bus_enable(FuriHalBus);
void furi_hal_bus_disable(FuriHalBus);
uint32_t furi_hal_resource_lease_try_acquire(uint32_t);
bool furi_hal_resource_lease_release(uint32_t,uint32_t);
void furi_hal_pwm_start(FuriHalPwmOutputId,uint32_t,uint8_t);
void furi_hal_pwm_stop(FuriHalPwmOutputId);
bool furi_hal_pwm_is_running(FuriHalPwmOutputId);
void furi_hal_pwm_set_params(FuriHalPwmOutputId,uint32_t,uint8_t);
#define LABMATE_PWM_CUSTOM_INDEX 15U
#define LABMATE_PWM_PRESET_COUNT 15U
typedef struct {
    bool generator_running, generator_state, generator_editing;
    bool generator_blocked, generator_release_fault;
    uint8_t generator_freq_index,generator_duty_percent;
    uint32_t generator_custom_hz,generator_custom_draft_hz;
    uint8_t generator_custom_step_index,generator_edit_original_index;
} LabMateApp;
bool labmate_pwm_settings_valid(uint32_t,uint8_t);
uint8_t labmate_pwm_adjust_duty(uint8_t,int8_t);
uint32_t labmate_pwm_adjust_hz(uint32_t,int8_t,uint32_t);
void labmate_generator_start(LabMateApp*);
void labmate_generator_stop(LabMateApp*);
void labmate_generator_change_frequency(LabMateApp*,int8_t);
void labmate_generator_change_duty(LabMateApp*,int8_t);
'''
RUN=r'''
#include "mock_hal.h"
#include <stdio.h>
bool labmate_pwm_settings_valid(uint32_t hz,uint8_t duty) {
    return hz>=1U && hz<=50000U && duty>=5U && duty<=95U;
}
uint8_t labmate_pwm_adjust_duty(uint8_t duty,int8_t dir) {
    return (uint8_t)(duty+(dir>0?1:-1));
}
uint32_t labmate_pwm_adjust_hz(uint32_t hz,int8_t dir,uint32_t step) {
    return dir>0?hz+step:hz-step;
}
#define CHECK(x) do{if(!(x)){fprintf(stderr,"E11 REAL JOINT PWM FAIL: %d %s\n",__LINE__,#x);abort();}}while(0)
int main(void) {
    LabMateApp app={.generator_freq_index=7,.generator_duty_percent=50,
                    .generator_custom_hz=1000};
    uint32_t monitor=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_MONITOR_PA7);
    CHECK(monitor);
    unsigned before=mock_ll_writes;
    labmate_generator_start(&app);
    CHECK(!app.generator_running && app.generator_blocked);
    CHECK(mock_ll_writes==before && !furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7));
    CHECK(furi_hal_resource_lease_release(monitor,FURI_HAL_LEASE_MONITOR_PA7));

    /* The App MUST NOT preclaim FURI_HAL_LEASE_PWM_PA7 here.
     * Only the real native HAL acquires it and starts the clock.
     */
    labmate_generator_start(&app);
    CHECK(app.generator_running && !app.generator_blocked);
    CHECK(furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7));
    CHECK(mock_ll_writes>before);
    CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7));
    before=mock_ll_writes;
    labmate_generator_change_frequency(&app,1);
    labmate_generator_change_duty(&app,1);
    CHECK(mock_ll_writes>before);
    labmate_generator_stop(&app);
    CHECK(!app.generator_running && !app.generator_release_fault);
    CHECK(!furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7));
    /* A full stop must give ownership back, verified through real C */
    monitor=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_MONITOR_PA7);
    CHECK(monitor);
    before=mock_ll_writes;
    labmate_generator_start(&app);
    CHECK(!app.generator_running && mock_ll_writes==before);
    CHECK(furi_hal_resource_lease_release(monitor,FURI_HAL_LEASE_MONITOR_PA7));
    labmate_generator_start(&app);
    CHECK(app.generator_running);
    labmate_generator_stop(&app);
    CHECK(!app.generator_running);

    puts("E11 JOINT REAL-C PASS: generator/native HAL sole-owner START, retune, BUSY, STOP, reenter.");
    puts("Not device PWM output, no cross-thread legacy timer guarantee.");
    return 0;
}
'''
def main() -> None:
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("momentum_root",type=Path)
    args=ap.parse_args()
    src=(args.momentum_root/"targets/f7/furi_hal/furi_hal_pwm.c").read_text()
    assert "native_pwm_try_claim" in src
    capability=(args.momentum_root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    assert "FURI_HAL_PWM_NATIVE_LEASE_API_V1" in capability
    assert "furi_hal_pwm_set_params" in src
    app=GENERATOR.read_text()
    assert "labmate_pwm_pa7_lease_handle" not in app
    spec=importlib.util.spec_from_file_location("native_pwm_test",NATIVE)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stubs=module.HOST.replace("int main(void){","int old_native_suite_not_run(void){")
    assert stubs!=module.HOST
    funcs=set(re.findall(r"\b(LL_[A-Za-z0-9_]+)\s*\(",src))
    constants=set(re.findall(r"\b(LL_[A-Z0-9_]+)\b",src))-funcs
    defs="\n".join(
        f"#define {fn}(...) do {{mock_ll_writes++;}} while(0)" for fn in sorted(funcs))
    defs+="\n"+"\n".join(f"#define {name} 1U" for name in sorted(constants))
    with tempfile.TemporaryDirectory(prefix="labmate_e11_joint_pwm_") as td:
        root=Path(td)
        (root/"mock_hal.h").write_text(HEADER+"\n"+defs+"\n")
        for h in ("labmate_generator.h","furi_hal_pwm.h","furi_hal_resources.h",
                  "furi_hal_bus.h","stm32wbxx_ll_tim.h",
                  "stm32wbxx_ll_lptim.h","stm32wbxx_ll_rcc.h","furi.h"):
            (root/h).write_text('#include "mock_hal.h"\n')
        (root/"firmware_native_pwm.c").write_text(src)
        (root/"labmate_generator.c").write_text(app)
        (root/"native_stubs.c").write_text(stubs)
        (root/"joint.c").write_text(RUN)
        exe=root/"joint"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-Wno-unused-variable","-I",str(root),
                        str(root/"firmware_native_pwm.c"),
                        str(root/"labmate_generator.c"),
                        str(root/"native_stubs.c"),str(root/"joint.c"),
                        "-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
if __name__=="__main__": main()
