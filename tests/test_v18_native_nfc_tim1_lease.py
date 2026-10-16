#!/usr/bin/env python3
"""Execute ACTUAL pinned patched NFC TIM1/TIM17 C + firmware resource C.

Host-fault instrumentation; never accesses Flipper hardware/USB/flash.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

HAL = r"""
#pragma once
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

#define furi_check(x) assert(x)
#define TAG "NFC test"
typedef int FuriHalBus;
typedef int FuriHalInterruptId;
typedef int IRQn_Type;
typedef int FuriHalNfcEventInternalType;
typedef struct {
    uint32_t id;
    bool counter_on;
} TIM_TypeDef;
extern TIM_TypeDef tim1, tim17;
#define TIM1 (&tim1)
#define TIM17 (&tim17)
#define FuriHalBusTIM1 1
#define FuriHalBusTIM17 17
#define FuriHalInterruptIdTim1UpTim16 101
#define FuriHalInterruptIdTim1TrgComTim17 117
#define TIM1_UP_TIM16_IRQn 101
#define TIM1_TRG_COM_TIM17_IRQn 117
#define FuriHalNfcEventInternalTypeTimerFwtExpired 1
#define FuriHalNfcEventInternalTypeTimerBlockTxExpired 2
#define LL_TIM_ONEPULSEMODE_SINGLE 1
#define LL_TIM_COUNTERMODE_UP 1
#define LL_TIM_CLOCKSOURCE_INTERNAL 1
#define FURI_HAL_NFC_CARRIER_HZ 13560000UL
#define FURI_HAL_LEASE_NATIVE_NFC_TIMERS ((1U<<0)|(1U<<24))
#define SystemCoreClock 64000000UL
typedef struct {int32_t fwt,fdt;} FuriHalNfcPollerCompensation;
typedef struct {int32_t fdt;} FuriHalNfcListenerCompensation;
typedef struct {
    struct {FuriHalNfcPollerCompensation compensation;} poller;
    struct {FuriHalNfcListenerCompensation compensation;} listener;
} FuriHalNfcTechBase;
typedef struct {uint32_t mode,tech;} FuriHalNfc;
#define FuriHalNfcModePoller 0U
#define FuriHalNfcModeListener 1U
extern FuriHalNfc furi_hal_nfc;
extern const FuriHalNfcTechBase* furi_hal_nfc_tech[1];
extern int writes,claims,releases,events;
extern bool allow_claim,allow_release,clock1,clock17;
uint32_t furi_hal_resource_lease_try_acquire(uint32_t);
bool furi_hal_resource_lease_release(uint32_t,uint32_t);
bool furi_hal_bus_is_enabled(int);
void furi_hal_bus_enable(int);
void furi_hal_bus_disable(int);
void furi_hal_interrupt_set_isr(int,void(*)(void*),void*);
void furi_hal_nfc_event_set(int);
uint32_t NVIC_GetPriorityGrouping(void);
uint32_t NVIC_EncodePriority(uint32_t,uint32_t,uint32_t);
void NVIC_SetPriority(int,uint32_t);
void NVIC_EnableIRQ(int);
void NVIC_DisableIRQ(int);
#define LL_TIM_IsActiveFlag_UPDATE(t) (1)
#define LL_TIM_ClearFlag_UPDATE(t) ((void)(t),++writes)
#define LL_TIM_IsEnabledCounter(t) ((t)->counter_on)
#define LL_TIM_EnableCounter(t) ((t)->counter_on=true,++writes)
#define LL_TIM_DisableCounter(t) ((t)->counter_on=false,++writes)
#define LL_TIM_SetOnePulseMode(t,x) ((void)(t),(void)(x),++writes)
#define LL_TIM_EnableUpdateEvent(t) ((void)(t),++writes)
#define LL_TIM_SetCounterMode(t,x) ((void)(t),(void)(x),++writes)
#define LL_TIM_SetClockSource(t,x) ((void)(t),(void)(x),++writes)
#define LL_TIM_DisableIT_UPDATE(t) ((void)(t),++writes)
#define LL_TIM_SetPrescaler(t,x) ((void)(t),(void)(x),++writes)
#define LL_TIM_SetAutoReload(t,x) ((void)(t),(void)(x),++writes)
#define LL_TIM_GenerateEvent_UPDATE(t) ((void)(t),++writes)
#define LL_TIM_EnableIT_UPDATE(t) ((void)(t),++writes)
#define LL_TIM_SetCounter(t,x) ((void)(t),(void)(x),++writes)
"""

HOST = r"""
#include "stub.h"
TIM_TypeDef tim1={.id=1},tim17={.id=17};
int writes,claims,releases,events,active_irqs;
bool allow_claim,allow_release=true,clock1,clock17;
FuriHalNfc furi_hal_nfc={.mode=FuriHalNfcModePoller,.tech=0};
static const FuriHalNfcTechBase nfc_tech0={
    .poller={.compensation={.fwt=0,.fdt=0}},
    .listener={.compensation={.fdt=0}}
};
const FuriHalNfcTechBase* furi_hal_nfc_tech[1]={&nfc_tech0};
static void(*registered[2])(void*);
static void* contexts[2];
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
    assert(mask==FURI_HAL_LEASE_NATIVE_NFC_TIMERS);claims++;
    return allow_claim?77U:0U;
}
bool furi_hal_resource_lease_release(uint32_t handle,uint32_t mask) {
    assert(handle==77U && mask==FURI_HAL_LEASE_NATIVE_NFC_TIMERS);
    releases++;
    return allow_release;
}
bool furi_hal_bus_is_enabled(int bus) {
    assert(bus==1||bus==17);
    return bus==1?clock1:clock17;
}
void furi_hal_bus_enable(int bus) {
    assert(!furi_hal_bus_is_enabled(bus));
    if(bus==1)clock1=true;else clock17=true;
    writes++;
}
void furi_hal_bus_disable(int bus) {
    assert(furi_hal_bus_is_enabled(bus));
    if(bus==1)clock1=false;else clock17=false;
    writes++;
}
void furi_hal_interrupt_set_isr(int id,void(*cb)(void*),void* ctx) {
    assert(id==101||id==117);
    int slot=id==101?0:1;
    registered[slot]=cb;contexts[slot]=ctx;
    if(cb)active_irqs++;else active_irqs--;
    writes++;
}
void furi_hal_nfc_event_set(int e) {assert(e==1||e==2);events++;}
uint32_t NVIC_GetPriorityGrouping(void){return 0U;}
uint32_t NVIC_EncodePriority(uint32_t a,uint32_t b,uint32_t c) {
    (void)a;(void)b;(void)c;return 0U;
}
void NVIC_SetPriority(int n,uint32_t priority){(void)n;(void)priority;writes++;}
void NVIC_EnableIRQ(int n){(void)n;writes++;}
void NVIC_DisableIRQ(int n){(void)n;writes++;}
#include "furi_hal_nfc_timer.c"
int main(void) {
    assert(!furi_hal_nfc_timers_init());
    assert(writes==0 && claims==1 && releases==0);
    furi_hal_nfc_timer_fwt_start(10000U);
    furi_hal_nfc_timer_fwt_stop();
    furi_hal_nfc_timers_deinit();
    assert(writes==0 && !nfc_e11_handle && events==0);
    /* Clock pre-enabled by legacy RFID/iButton, no TIM/IRQ writes. */
    allow_claim=true;
    clock1=true;
    assert(!furi_hal_nfc_timers_init());
    assert(writes==0 && releases==1 && !nfc_e11_handle);
    clock1=false;clock17=true;
#ifdef TEST_PREFLIGHT_RELEASE_FAULT
    allow_release=false;
    assert(!furi_hal_nfc_timers_init());
    assert(writes==0 && nfc_e11_handle==77U && nfc_e11_fault);
    int c=claims;
    clock17=false;
    assert(!furi_hal_nfc_timers_init());
    assert(claims==c && writes==0);
    puts("E11 NFC PRE-FLIGHT STICKY FAILED RELEASE REAL C PASS");
    return 0;
#endif
    assert(!furi_hal_nfc_timers_init());
    assert(writes==0 && releases==2 && !nfc_e11_handle);
    clock17=false;
    assert(furi_hal_nfc_timers_init());
    assert(clock1 && clock17 && nfc_e11_handle==77U && active_irqs==2);
    assert(registered[0] && registered[1]);
    registered[0](contexts[0]);
    assert(events==1);
    furi_hal_nfc_timer_fwt_start(10000U);
    assert(tim1.counter_on);
    furi_hal_nfc_timer_fwt_stop();
    assert(!tim1.counter_on);
    furi_hal_nfc_timer_block_tx_start_us(100U);
    assert(tim17.counter_on);
    furi_hal_nfc_timer_block_tx_stop();
    assert(!tim17.counter_on);
    furi_hal_nfc_timers_deinit();
    assert(!clock1 && !clock17 && active_irqs==0);
    assert(!nfc_e11_handle && releases==3);
#ifdef TEST_STOP_RELEASE_FAULT
    assert(furi_hal_nfc_timers_init());
    allow_release=false;
    furi_hal_nfc_timers_deinit();
    assert(!clock1 && !clock17 && !active_irqs);
    assert(nfc_e11_handle==77U && nfc_e11_fault && releases==4);
    int w=writes,c=claims;
    furi_hal_nfc_timers_deinit();
    assert(!furi_hal_nfc_timers_init());
    furi_hal_nfc_timer_fwt_stop();
    furi_hal_nfc_timer_fwt_start(10000U);
    assert(writes==w && claims==c);
#else
    assert(furi_hal_nfc_timers_init());
    /* Native clock lost asynchronously. Do not disable other ISR/clock. */
    clock1=false;
    int w=writes,c=claims;
    furi_hal_nfc_timer_fwt_stop();
    furi_hal_nfc_timers_deinit();
    assert(writes==w && claims==c && nfc_e11_fault);
    assert(nfc_e11_handle==77U);
    assert(!furi_hal_nfc_timers_init());
    assert(writes==w);
#endif
    puts("E11 NFC ACTUAL C HOST PASS: dual timer, IRQ, deny, START/STOP, sticky fault");
    return 0;
}
"""

LEASE_TEST = r"""
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"E11 NFC MASK FAIL %d\n",__LINE__);exit(1);}}while(0)
int main(void) {
    uint32_t h=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_TIMERS);
    REQUIRE(h);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7)==0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1)==0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_TIMERS)==0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3)!=0U);
    REQUIRE(!furi_hal_resource_lease_release(h,FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1));
    REQUIRE(furi_hal_resource_lease_release(h,FURI_HAL_LEASE_NATIVE_NFC_TIMERS));
    REQUIRE(!furi_hal_resource_lease_release(h,FURI_HAL_LEASE_NATIVE_NFC_TIMERS));
    uint32_t pwm=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7);
    REQUIRE(pwm);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_TIMERS)==0U);
    REQUIRE(furi_hal_resource_lease_release(pwm,FURI_HAL_LEASE_PWM_PA7));
    puts("E11 NFC REAL FIRMWARE RESOURCE C PASS: TIM1+TIM17 atomic mask and PWM/iButton collision");
    return 0;
}
"""

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("momentum_root",type=Path)
    a=ap.parse_args()
    root=a.momentum_root.resolve()
    s=(root/"targets/f7/furi_hal/furi_hal_nfc_timer.c").read_text()
    nfc=(root/"targets/f7/furi_hal/furi_hal_nfc.c").read_text()
    private=(root/"targets/f7/furi_hal/furi_hal_nfc_i.h").read_text()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    r=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    assert "/* LabMate E11 native NFC TIM1/TIM17 owner. */" in s
    assert "FURI_HAL_LEASE_NATIVE_NFC_TIMERS" in h
    assert "mask == FURI_HAL_LEASE_NATIVE_NFC_TIMERS" in r
    assert "bool furi_hal_nfc_timers_init(void);" in private
    resume=nfc[nfc.index("FuriHalNfcError furi_hal_nfc_low_power_mode_stop(void)"):nfc.index(
        "static FuriHalNfcError furi_hal_nfc_poller_init_common")]
    assert resume.index("if(!furi_hal_nfc_timers_init())") < resume.index(
        "furi_hal_nfc_init_gpio_isr();")
    assert "error = FuriHalNfcErrorBusy;" in resume
    assert "furi_hal_nfc_deinit_gpio_isr();" in resume
    assert "furi_hal_nfc_timers_deinit();" in resume
    assert "if(!nfc_e11_ready()) return;" in s
    assert "nfc_e11_fault = true;" in s
    assert "FURI_HAL_NFC_TIMER_DEBUG" in s and "#error" in s
    assert "FuriHalLeaseTim17 = (1U << 24)" in h

    with tempfile.TemporaryDirectory(prefix="labmate_e11_nfc_") as td:
        tmp=Path(td)
        (tmp/"stub.h").write_text(HAL)
        (tmp/"furi_hal_nfc_timer.c").write_text(s)
        for inc in ("furi_hal_nfc_i.h","furi_hal_nfc_tech_i.h","stm32wbxx_ll_tim.h",
                    "furi_hal_interrupt.h","furi_hal_resources.h","furi_hal_bus.h"):
            (tmp/inc).write_text("")
        exe=tmp/"host"
        (tmp/"host.c").write_text(HOST)
        for flag in ([],["-DTEST_STOP_RELEASE_FAULT"],["-DTEST_PREFLIGHT_RELEASE_FAULT"]):
            subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                            "-O0",*flag,"-I",str(tmp),str(tmp/"host.c"),"-o",str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
        pre=r"""
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
        hs=h[h.index("enum {\n    FuriHalLeaseTim1"):h.index("/* Returns unique nonzero")]
        body=r[r.index("/* Firmware-owned E11 lease primitive"):r.index(
            "const GpioPinRecord* furi_hal_resources_pin_by_number")]
        (tmp/"lease.c").write_text(pre+hs+body+LEASE_TEST)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-pthread",str(tmp/"lease.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 NFC REAL C HOST 3/3 + resource allocator PASS (NO DEVICE/FLASH)")

if __name__=="__main__":
    main()
