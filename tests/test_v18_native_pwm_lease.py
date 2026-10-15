#!/usr/bin/env python3
"""Compile AND execute exact patched Momentum furi_hal_pwm.c with fake HAL.

Tests actual native PWM driver source, not a model or substitute.
Never accesses a device; only a pinned ephemeral firmware checkout.
"""
from __future__ import annotations
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

MARKER = "/* LabMate E11 native PWM lease owner: scoped to PWM HAL service."

HOST = r'''
#include "mock_hal.h"
#include <stdio.h>

const GpioPin gpio_ext_pa7 = {7};
const GpioPin gpio_ext_pa4 = {4};
unsigned mock_ll_writes;
static unsigned gpio_changes,bus_changes,lease_claims,lease_releases;
static bool fail_release;
static bool tim1_on,lptim2_on;
static uint32_t used, next_handle;
static struct {uint32_t id,mask;} claims[32];

static bool* bus_state(FuriHalBus bus) {
    if(bus==FuriHalBusTIM1) return &tim1_on;
    if(bus==FuriHalBusLPTIM2) return &lptim2_on;
    abort();
}
void furi_hal_gpio_init_ex(
    const GpioPin* pin,int mode,int pull,int speed,int alt) {
    (void)mode;(void)pull;(void)speed;(void)alt;
    assert(pin==&gpio_ext_pa7 || pin==&gpio_ext_pa4);
    assert(used & (pin==&gpio_ext_pa7 ? FURI_HAL_LEASE_MONITOR_PA7 :
                     FURI_HAL_LEASE_MONITOR_PA4));
    gpio_changes++;
}
void furi_hal_gpio_init_simple(const GpioPin* pin,int mode) {
    assert(mode==GpioModeAnalog);
    furi_hal_gpio_init_ex(pin,mode,0,0,0);
}
bool furi_hal_bus_is_enabled(FuriHalBus bus){return *bus_state(bus);}
void furi_hal_bus_enable(FuriHalBus bus){
    assert(!*bus_state(bus));
    *bus_state(bus)=true;bus_changes++;
}
void furi_hal_bus_disable(FuriHalBus bus){
    assert(*bus_state(bus));
    *bus_state(bus)=false;bus_changes++;
}
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask){
    assert(mask==FURI_HAL_LEASE_PWM_PA7 ||
           mask==FURI_HAL_LEASE_MONITOR_PA4 ||
           mask==FURI_HAL_LEASE_MONITOR_PA7 ||
           mask==FURI_HAL_LEASE_ONEWIRE_PA4);
    lease_claims++;
    if(mask & used) return 0U;
    uint32_t id=++next_handle;
    assert(id<32);
    claims[id].id=id;claims[id].mask=mask;
    used|=mask;
    return id;
}
bool furi_hal_resource_lease_release(uint32_t id,uint32_t mask){
    lease_releases++;
    if(fail_release)return false;
    if(id==0U || id>=32U || claims[id].id!=id || claims[id].mask!=mask)
        return false;
    used&=~mask;
    claims[id].id=0U;claims[id].mask=0U;
    return true;
}
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"HOST FAIL line %d: %s\n",__LINE__,#x);abort();}}while(0)
int main(void){
    /* A LabMate lease on PA7 denies native TIM1 PWM before ANY registers. */
    uint32_t monitor=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_MONITOR_PA7);
    REQUIRE(monitor);
    furi_hal_pwm_start(FuriHalPwmOutputIdTim1PA7,1000U,50U);
    REQUIRE(!furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7));
    REQUIRE(gpio_changes==0U && bus_changes==0U && mock_ll_writes==0U);
    furi_hal_pwm_set_params(FuriHalPwmOutputIdTim1PA7,0U,50U);
    furi_hal_pwm_stop(FuriHalPwmOutputIdTim1PA7);
    REQUIRE(gpio_changes==0U && bus_changes==0U && mock_ll_writes==0U);
    REQUIRE(furi_hal_resource_lease_release(monitor,FURI_HAL_LEASE_MONITOR_PA7));

    furi_hal_pwm_start(FuriHalPwmOutputIdTim1PA7,1000U,50U);
    REQUIRE(furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7));
    REQUIRE(gpio_changes==1U && tim1_on && mock_ll_writes>0U);
    REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7));
    REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_MONITOR_PA7));
    unsigned writes=mock_ll_writes;
    furi_hal_pwm_set_params(FuriHalPwmOutputIdTim1PA7,2000U,60U);
    REQUIRE(mock_ll_writes>writes);
    furi_hal_pwm_stop(FuriHalPwmOutputIdTim1PA7);
    REQUIRE(!tim1_on && !furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7));
    REQUIRE(used==0U);
    unsigned pins=gpio_changes;
    furi_hal_pwm_stop(FuriHalPwmOutputIdTim1PA7);
    REQUIRE(gpio_changes==pins);

    /* Even without a claimed lease, a legacy-enabled TIM1 bus is a
     * denial; the short temporary claim must be released unmodified. */
    tim1_on=true;
    pins=gpio_changes;
    writes=mock_ll_writes;
    furi_hal_pwm_start(FuriHalPwmOutputIdTim1PA7,1000U,50U);
    REQUIRE(!furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7));
    REQUIRE(gpio_changes==pins && mock_ll_writes==writes && used==0U);
    tim1_on=false;

    /* PA4 native PWM must coexist safely with cooperative 1-Wire. */
    uint32_t onewire=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_ONEWIRE_PA4);
    REQUIRE(onewire);
    pins=gpio_changes;
    furi_hal_pwm_start(FuriHalPwmOutputIdLptim2PA4,1000U,50U);
    REQUIRE(!furi_hal_pwm_is_running(FuriHalPwmOutputIdLptim2PA4));
    REQUIRE(gpio_changes==pins && !lptim2_on);
    REQUIRE(furi_hal_resource_lease_release(onewire,FURI_HAL_LEASE_ONEWIRE_PA4));
    furi_hal_pwm_start(FuriHalPwmOutputIdLptim2PA4,1000U,50U);
    REQUIRE(furi_hal_pwm_is_running(FuriHalPwmOutputIdLptim2PA4));
    REQUIRE(gpio_changes==pins+1U && lptim2_on);
    REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_ONEWIRE_PA4));
    REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_MONITOR_PA4));
    furi_hal_pwm_stop(FuriHalPwmOutputIdLptim2PA4);
    REQUIRE(!lptim2_on && used==0U);

    /* Failed exact firmware release is sticky, never reconfigure
     * a pin again while a firmware handle might still be valid. */
    furi_hal_pwm_start(FuriHalPwmOutputIdLptim2PA4,1000U,50U);
    REQUIRE(lptim2_on);
    fail_release=true;
    furi_hal_pwm_stop(FuriHalPwmOutputIdLptim2PA4);
    REQUIRE(!lptim2_on && (used & FURI_HAL_LEASE_MONITOR_PA4));
    pins=gpio_changes;
    writes=mock_ll_writes;
    furi_hal_pwm_start(FuriHalPwmOutputIdLptim2PA4,1000U,50U);
    furi_hal_pwm_set_params(FuriHalPwmOutputIdLptim2PA4,1000U,50U);
    furi_hal_pwm_stop(FuriHalPwmOutputIdLptim2PA4);
    REQUIRE(gpio_changes==pins && mock_ll_writes==writes);
    REQUIRE(!furi_hal_pwm_is_running(FuriHalPwmOutputIdLptim2PA4));
    REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_ONEWIRE_PA4));
    REQUIRE(lease_claims>0U && lease_releases>0U);
    puts("E11 NATIVE PWM REAL MOMENTUM C HOST PASS: TIM1/PA7 + LPTIM2/PA4.");
    puts("Source compiled against fake HAL; NOT physical device or global service arbitration.");
    return 0;
}
'''
def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("momentum_root",type=Path)
    args=ap.parse_args()
    root=args.momentum_root.resolve()
    source=root/"targets/f7/furi_hal/furi_hal_pwm.c"
    text=source.read_text(encoding="utf-8")
    assert text.count(MARKER)==1, "E11 PWM firmware patch not present"
    assert "if(!native_pwm_try_claim(channel)) return;" in text
    assert "native_pwm_release(&native_pwm_tim1_pa7_handle" in text
    assert "native_pwm_release(&native_pwm_lptim2_pa4_handle" in text

    funcs=set(re.findall(r"\b(LL_[A-Za-z0-9_]+)\s*\(",text))
    constants=set(re.findall(r"\b(LL_[A-Z0-9_]+)\b",text))
    constants-=funcs
    macros="\n".join(
        f"#define {name}(...) do {{mock_ll_writes++;}} while(0)" for name in sorted(funcs)
    )
    macros+="\n"+"\n".join(f"#define {name} 1U" for name in sorted(constants))
    mock_header=r"""
#ifndef LABMATE_NATIVE_PWM_FAKE
#define LABMATE_NATIVE_PWM_FAKE
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <assert.h>
typedef enum {
    FuriHalPwmOutputIdNone,
    FuriHalPwmOutputIdTim1PA7,
    FuriHalPwmOutputIdLptim2PA4
} FuriHalPwmOutputId;
typedef enum { FuriHalBusTIM1, FuriHalBusLPTIM2 } FuriHalBus;
typedef struct {int pin;} GpioPin;
extern const GpioPin gpio_ext_pa7,gpio_ext_pa4;
extern unsigned mock_ll_writes;
#define FURI_HAL_LEASE_PWM_PA7 ((1U<<0)|(1U<<1))
#define FURI_HAL_LEASE_MONITOR_PA7 (1U<<1)
#define FURI_HAL_LEASE_MONITOR_PA4 (1U<<11)
#define FURI_HAL_LEASE_ONEWIRE_PA4 (1U<<11)
#define FURI_HAL_RESOURCE_LEASE_API_V1 1
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
"""
    with tempfile.TemporaryDirectory(prefix="labmate_e11_native_pwm_") as td:
        tmp=Path(td)
        (tmp/"mock_hal.h").write_text(mock_header+"\n"+macros+"\n#endif\n",encoding="utf-8")
        for h in (
            "furi_hal_pwm.h","furi_hal_resources.h","furi_hal_bus.h",
            "stm32wbxx_ll_tim.h","stm32wbxx_ll_lptim.h","stm32wbxx_ll_rcc.h","furi.h"
        ):
            (tmp/h).write_text('#include "mock_hal.h"\n',encoding="utf-8")
        (tmp/"host.c").write_text(HOST,encoding="utf-8")
        exe=tmp/"test"
        subprocess.run(
            ["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
             "-I",str(tmp),str(source),str(tmp/"host.c"),"-o",str(exe)],
            check=True,
        )
        subprocess.run([str(exe)],check=True)

if __name__=="__main__":
    main()
