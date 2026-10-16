#!/usr/bin/env python3
"""E11 actual native iButton C host tests and exact firmware mask arbitration.

Consumes the patched native Momentum source. NO device/USB/flash.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#pragma once
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
typedef void (*FuriHalIbuttonEmulateCallback)(void*);
#define UNUSED(x) (void)(x)
#define FURI_LOG_I(...) ((void)0)
#define furi_check(x) assert(x)
#define FURI_HAL_IBUTTON_FAKE_STUB 1
#define FuriHalBusTIM1 1
#define FuriHalInterruptIdTim1UpTim16 2
#define TIM1 1
#define LL_TIM_COUNTERMODE_UP 1
#define LL_TIM_CLOCKDIVISION_DIV1 1
#define LL_TIM_CLOCKSOURCE_INTERNAL 1
#define FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1 (1U<<0)
#define GpioModeOutputOpenDrain 1
#define GpioModeAnalog 2
#define GpioPullNo 0
#define GpioSpeedLow 0
typedef struct {uint32_t x;} GpioPin;
extern const GpioPin gpio_ibutton;
extern int hardware_writes,callback_calls,claims,releases;
extern bool lease_available,release_ok,bus_enabled;
uint32_t furi_hal_resource_lease_try_acquire(uint32_t);
bool furi_hal_resource_lease_release(uint32_t,uint32_t);
bool furi_hal_bus_is_enabled(int);
void furi_hal_bus_enable(int);
void furi_hal_bus_disable(int);
void furi_hal_interrupt_set_isr(int, void (*)(void*), void*);
void furi_hal_gpio_write(const GpioPin*,bool);
void furi_hal_gpio_init(const GpioPin*,int,int,int);
void furi_hal_ibutton_pin_configure(void);
#define LL_TIM_IsActiveFlag_UPDATE(...) 1
#define LL_TIM_ClearFlag_UPDATE(...) (++hardware_writes)
#define LL_TIM_SetPrescaler(...) (++hardware_writes)
#define LL_TIM_SetCounterMode(...) (++hardware_writes)
#define LL_TIM_SetAutoReload(timer, value) ((void)(timer),(void)(value),++hardware_writes)
#define LL_TIM_DisableARRPreload(...) (++hardware_writes)
#define LL_TIM_SetRepetitionCounter(...) (++hardware_writes)
#define LL_TIM_SetClockDivision(...) (++hardware_writes)
#define LL_TIM_SetClockSource(...) (++hardware_writes)
#define LL_TIM_GenerateEvent_UPDATE(...) (++hardware_writes)
#define LL_TIM_EnableIT_UPDATE(...) (++hardware_writes)
#define LL_TIM_EnableCounter(...) (++hardware_writes)
#define LL_TIM_DisableCounter(...) (++hardware_writes)
"""
HARNESS=r"""
#include "stub.h"
int hardware_writes,callback_calls,claims,releases;
bool lease_available,release_ok=true,bus_enabled;
const GpioPin gpio_ibutton={0};
static void (*active_irq)(void*);
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
    assert(mask==FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1);
    claims++;
    return lease_available?99U:0U;
}
bool furi_hal_resource_lease_release(uint32_t h,uint32_t mask) {
    assert(h==99U && mask==FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1);
    releases++;
    return release_ok;
}
bool furi_hal_bus_is_enabled(int b) { assert(b==FuriHalBusTIM1);return bus_enabled; }
void furi_hal_bus_enable(int b) {assert(b==FuriHalBusTIM1);assert(!bus_enabled);bus_enabled=true;hardware_writes++;}
void furi_hal_bus_disable(int b) {assert(b==FuriHalBusTIM1);assert(bus_enabled);bus_enabled=false;hardware_writes++;}
void furi_hal_interrupt_set_isr(int n,void(*cb)(void*),void* ctx) {
    assert(n==FuriHalInterruptIdTim1UpTim16);assert(ctx==NULL);
    active_irq=cb;hardware_writes++;
}
void furi_hal_gpio_write(const GpioPin* p,bool x){(void)p;(void)x;hardware_writes++;}
void furi_hal_gpio_init(const GpioPin* p,int m,int a,int b){
    (void)p;(void)m;(void)a;(void)b;hardware_writes++;
}
#include "furi_hal_ibutton.c"
static void callback(void* p){ assert(p==NULL);callback_calls++; }
int main(void) {
    furi_hal_ibutton_init();
    assert(furi_hal_ibutton->state==FuriHalIbuttonStateIdle);
    assert(!furi_hal_ibutton->e11_lease_handle);
    /* Denied native owner must not set running, timer, ISR or callback. */
    furi_hal_ibutton_emulate_start(100U,callback,NULL);
    assert(claims==1 && hardware_writes==0 && !active_irq);
    assert(furi_hal_ibutton->state==FuriHalIbuttonStateIdle);
    furi_hal_ibutton_emulate_set_next(200U);
    furi_hal_ibutton_emulate_stop();
    assert(!hardware_writes && !releases);
    /* Legacy native HAL already enabled TIM1 but never took a lease. */
    lease_available=true;
    bus_enabled=true;
    furi_hal_ibutton_emulate_start(100U,callback,NULL);
    assert(claims==2 && releases==1 && hardware_writes==0 && !active_irq);
    assert(!furi_hal_ibutton->e11_lease_handle);
    bus_enabled=false;
    /* Genuine ownership -> start, ISR, period update and STOP. */
    furi_hal_ibutton_emulate_start(100U,callback,NULL);
    assert(furi_hal_ibutton->state==FuriHalIbuttonStateRunning);
    assert(furi_hal_ibutton->e11_lease_handle==99U && bus_enabled && active_irq);
    active_irq(NULL);
    assert(callback_calls==1);
    int w=hardware_writes;
    furi_hal_ibutton_emulate_set_next(220U);
    assert(hardware_writes==w+1);
    furi_hal_ibutton_emulate_stop();
    assert(!bus_enabled && !active_irq);
    assert(furi_hal_ibutton->state==FuriHalIbuttonStateIdle);
    assert(!furi_hal_ibutton->e11_lease_handle && releases==2);
    w=hardware_writes;
    furi_hal_ibutton_emulate_stop();
    furi_hal_ibutton_emulate_set_next(5U);
    assert(hardware_writes==w && releases==2);
#ifdef TEST_RELEASE_FAULT
    /* STOP must not report reusable TIM1 after firmware refuses release.
     * HAL timer and ISR teardown is our own and runs before release.
     */
    release_ok=false;
    furi_hal_ibutton_emulate_start(50U,callback,NULL);
    assert(bus_enabled && furi_hal_ibutton->e11_lease_handle);
    furi_hal_ibutton_emulate_stop();
    assert(!bus_enabled && !active_irq);
    assert(furi_hal_ibutton->e11_lease_fault);
    assert(furi_hal_ibutton->e11_lease_handle==99U && releases==3);
    w=hardware_writes;
    furi_hal_ibutton_emulate_start(123U,callback,NULL);
    furi_hal_ibutton_emulate_set_next(45U);
    furi_hal_ibutton_emulate_stop();
    assert(hardware_writes==w && releases==3);
    return 0;
#endif
    /* If another service kills the clock during emulation, do not call
     * bus_disable or touch another owner ISR, keep our claim sticky.
     */
    furi_hal_ibutton_emulate_start(50U,callback,NULL);
    assert(bus_enabled && furi_hal_ibutton->e11_lease_handle);
    bus_enabled=false;
    w=hardware_writes;
    furi_hal_ibutton_emulate_set_next(123U);
    furi_hal_ibutton_emulate_stop();
    assert(hardware_writes==w && releases==2);
    assert(furi_hal_ibutton->e11_lease_fault);
    assert(furi_hal_ibutton->e11_lease_handle==99U);
    active_irq(NULL);
    assert(callback_calls==1);
    return 0;
}
"""
RESOURCE_PRE=r"""
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
static pthread_mutex_t critical=PTHREAD_MUTEX_INITIALIZER;
#define FURI_CRITICAL_ENTER() do{if(pthread_mutex_lock(&critical))abort();}while(0)
#define FURI_CRITICAL_EXIT() do{if(pthread_mutex_unlock(&critical))abort();}while(0)
"""
RESOURCE_RUN=r"""
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"IBUTTON RESOURCE FAIL line %d\n",__LINE__);exit(1);}}while(0)
int main(void) {
    uint32_t a=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1);
    REQUIRE(a);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7)==0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1)==0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3)!=0U);
    REQUIRE(!furi_hal_resource_lease_release(a,FURI_HAL_LEASE_PWM_PA7));
    REQUIRE(furi_hal_resource_lease_release(a,FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1));
    REQUIRE(!furi_hal_resource_lease_release(a,FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1));
    uint32_t pwm=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7);
    REQUIRE(pwm);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1)==0U);
    REQUIRE(furi_hal_resource_lease_release(pwm,FURI_HAL_LEASE_PWM_PA7));
    puts("E11 NATIVE IBUTTON ACTUAL RESOURCE C TIM1/PWM EXCLUSION PASS");
    return 0;
}
"""

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("momentum_root",type=Path)
    args=ap.parse_args()
    root=args.momentum_root.resolve()
    path=root/"targets/f7/furi_hal/furi_hal_ibutton.c"
    source=path.read_text()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    rs=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    assert "/* E11 native iButton TIM1 cooperative lease (timer only)." in source
    assert "FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1" in h
    assert "mask == FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1" in rs
    assert source.index("furi_hal_resource_lease_try_acquire(") < source.index(
        "furi_hal_ibutton->state = FuriHalIbuttonStateRunning;",source.index("bool furi_hal_ibutton_emulate_try_start_with_pin"))
    with tempfile.TemporaryDirectory(prefix="labmate_e11_ibutton_") as td:
        root_tmp=Path(td)
        (root_tmp/"stub.h").write_text(STUB)
        (root_tmp/"furi_hal_ibutton.c").write_text(source)
        for inc in ("furi_hal_ibutton.h","furi_hal_interrupt.h","furi_hal_resources.h",
                    "furi_hal_bus.h","stm32wbxx_ll_tim.h","furi.h"):
            (root_tmp/inc).write_text("")
        (root_tmp/"host.c").write_text(HARNESS)
        exe=root_tmp/"test"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic","-O0",
                        "-I",str(root_tmp),str(root_tmp/"host.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-O0","-DTEST_RELEASE_FAULT=1","-I",str(root_tmp),
                        str(root_tmp/"host.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
        masks_start=h.index("enum {\n    FuriHalLeaseTim1")
        masks_end=h.index("/* Returns unique nonzero",masks_start)
        source_start=rs.index("/* Firmware-owned E11 lease primitive")
        source_end=rs.index("const GpioPinRecord* furi_hal_resources_pin_by_number",source_start)
        (root_tmp/"resource.c").write_text(
            RESOURCE_PRE+h[masks_start:masks_end]+rs[source_start:source_end]+RESOURCE_RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-pthread",str(root_tmp/"resource.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 NATIVE IBUTTON ACTUAL C HOST PASS: BUSY zero writes, native TIM1 start/STOP,")
    print("legacy clock already enabled, ISR/retune guards, sticky unexpected clock loss.")
    print("Still NOT global TIM1 firmware safety or physical PASS.")

if __name__=="__main__":
    main()
