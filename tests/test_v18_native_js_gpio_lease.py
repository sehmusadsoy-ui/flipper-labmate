#!/usr/bin/env python3
"""Test source-extracted native JS GPIO claim helper, and gate cleanup call sites.

Not a JS runtime test. Full patched Momentum firmware compile is separate.
"""
from __future__ import annotations
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

PRELUDE=r'''
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <stdlib.h>
typedef struct { unsigned n; } GpioPin;
typedef enum { FuriHalPwmOutputIdNone,FuriHalPwmOutputIdTim1PA7,
    FuriHalPwmOutputIdLptim2PA4 } FuriHalPwmOutputId;
typedef struct {
    const GpioPin* pin;
    FuriHalPwmOutputId pwm_output;
    uint32_t lease_handle,lease_mask;
    bool lease_fault,configured,pwm_owned;
} JsGpioPinInst;
#define FURI_HAL_LEASE_MONITOR_PC0 (1U<<5)
#define FURI_HAL_LEASE_MONITOR_PC1 (1U<<7)
#define FURI_HAL_LEASE_MONITOR_PC3 (1U<<14)
#define FURI_HAL_LEASE_MONITOR_PB2 (1U<<9)
#define FURI_HAL_LEASE_MONITOR_PB3 (1U<<3)
#define FURI_HAL_LEASE_MONITOR_PA4 (1U<<11)
#define FURI_HAL_LEASE_MONITOR_PA6 (1U<<15)
#define FURI_HAL_LEASE_MONITOR_PA7 (1U<<1)
#define PIN_DEF(name,number) const GpioPin gpio_ext_##name={number};
PIN_DEF(pc0,0) PIN_DEF(pc1,1) PIN_DEF(pc3,3) PIN_DEF(pb2,2)
PIN_DEF(pb3,33) PIN_DEF(pa4,4) PIN_DEF(pa6,6) PIN_DEF(pa7,7)
static bool native_pwm_running,deny_lease;
static uint32_t current_mask,live_handle,claimed_count;
bool furi_hal_pwm_is_running(FuriHalPwmOutputId p) {
    assert(p != FuriHalPwmOutputIdNone);
    return native_pwm_running;
}
uint32_t furi_hal_resource_lease_try_acquire(uint32_t m) {
    claimed_count++;
    if(deny_lease || (m & current_mask)) return 0U;
    current_mask |= m;
    return ++live_handle;
}
bool furi_hal_resource_lease_release(uint32_t h,uint32_t m) {
    (void)h;
    assert((current_mask & m)==m);
    current_mask &= ~m;
    return true;
}
'''
TESTS=r'''
static void exercise(const GpioPin* p,uint32_t expected) {
    JsGpioPinInst a={.pin=p};
    JsGpioPinInst b={.pin=p};
    assert(js_gpio_e11_monitor_mask(p)==expected);
    assert(js_gpio_e11_claim(&a));
    assert(a.lease_handle && a.lease_mask==expected);
    assert(current_mask==expected);
    assert(!js_gpio_e11_claim(&b));
    assert(js_gpio_e11_claim(&a)); /* no new firmware claim */
    assert(!js_gpio_e11_claim(&a)==false);
    uint32_t h=a.lease_handle;
    assert(furi_hal_resource_lease_release(h,expected));
    current_mask=0U;
}
int main(void) {
    const GpioPin* pins[]={
        &gpio_ext_pc0,&gpio_ext_pc1,&gpio_ext_pc3,&gpio_ext_pb2,
        &gpio_ext_pb3,&gpio_ext_pa4,&gpio_ext_pa6,&gpio_ext_pa7,
    };
    const uint32_t masks[]={
        FURI_HAL_LEASE_MONITOR_PC0,FURI_HAL_LEASE_MONITOR_PC1,
        FURI_HAL_LEASE_MONITOR_PC3,FURI_HAL_LEASE_MONITOR_PB2,
        FURI_HAL_LEASE_MONITOR_PB3,FURI_HAL_LEASE_MONITOR_PA4,
        FURI_HAL_LEASE_MONITOR_PA6,FURI_HAL_LEASE_MONITOR_PA7,
    };
    for(unsigned i=0;i<8;i++) exercise(pins[i],masks[i]);
    const GpioPin other={99U};
    JsGpioPinInst unknown={.pin=&other};
    assert(js_gpio_e11_claim(&unknown));
    assert(unknown.lease_handle==0U);
    JsGpioPinInst pa7={.pin=&gpio_ext_pa7,.pwm_output=FuriHalPwmOutputIdTim1PA7};
    native_pwm_running=true;
    assert(!js_gpio_e11_claim(&pa7));
    native_pwm_running=false;
    deny_lease=true;
    assert(!js_gpio_e11_claim(&pa7));
    deny_lease=false;
    assert(js_gpio_e11_claim(&pa7));
    pa7.lease_fault=true;
    assert(!js_gpio_e11_claim(&pa7));
    pa7.lease_fault=false;
    pa7.pwm_owned=true;
    assert(!js_gpio_e11_claim(&pa7));
    assert(furi_hal_resource_lease_release(pa7.lease_handle,pa7.lease_mask));
    puts("Native JS GPIO exact-claim helper HOST PASS: 8 pins, owner denial, PWM, old pins.");
    return 0;
}
'''
def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("firmware_root",type=Path)
    args=ap.parse_args()
    src=(args.firmware_root/"applications/system/js_app/modules/js_gpio.c").read_text()
    marker="/* LabMate E11 native JS GPIO connector-owner contract. */"
    assert src.count(marker)==1
    helper=src.split(marker,1)[1].split("ARRAY_DEF(ManagedPinsArray",1)[0]
    assert "js_gpio_e11_monitor_mask" in helper
    assert "js_gpio_e11_claim" in helper
    assert "calloc(1U, sizeof(JsGpioPinInst))" in src, "manager bookkeeping must be zeroed"
    assert "furi_hal_gpio_try_add_int_callback" in src
    assert "JS_ERROR_AND_RETURN(mjs, MJS_BAD_ARGS_ERROR, \"GPIO pin BUSY\")" in src
    assert "if(manager_data->configured && (!mask || manager_data->lease_handle))" in src
    assert "if(manager_data->pwm_owned)" in src
    assert "furi_hal_resource_lease_release(" in src
    # Prohibit obsolete destroy behavior that resets any merely inspected
    # connector pin, and prevent blind stopping of another native PWM.
    cleanup=src[src.index("static void js_gpio_destroy("):]
    assert "if(manager_data->configured && (!mask || manager_data->lease_handle))" in cleanup
    assert cleanup.index("if(manager_data->configured") < cleanup.index("furi_hal_resource_lease_release(")
    assert "if(manager_data->pwm_owned)" in cleanup
    with tempfile.TemporaryDirectory(prefix="labmate_e11_js_gpio_") as td:
        c=Path(td)/"mock.c"
        exe=Path(td)/"mock"
        c.write_text(PRELUDE+helper+TESTS)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        str(c),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
if __name__=="__main__": main()
