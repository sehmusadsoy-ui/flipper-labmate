#!/usr/bin/env python3
"""Compile actual patched Momentum lease primitive with native pulse masks.

Exercises firmware's exact real C acquisition/release logic, not a model.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import tempfile

RUN=r'''
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"E11 MASK FAIL %d: %s\n",__LINE__,#x);exit(1);}}while(0)
int main(void){
    const uint32_t masks[8]={
        FURI_HAL_LEASE_PULSE_PC0,FURI_HAL_LEASE_PULSE_PC1,
        FURI_HAL_LEASE_PULSE_PC3,FURI_HAL_LEASE_PULSE_PB2,
        FURI_HAL_LEASE_PULSE_PB3,FURI_HAL_LEASE_PULSE_PA4,
        FURI_HAL_LEASE_PULSE_PA6,FURI_HAL_LEASE_PULSE_PA7
    };
    for(size_t i=0;i<8;i++) {
        uint32_t h=furi_hal_resource_lease_try_acquire(masks[i]);
        REQUIRE(h!=0U);
        REQUIRE(furi_hal_resource_lease_try_acquire(masks[i])==0U);
        REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_NONCONNECTOR)==0U);
        REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3)==0U);
        REQUIRE(!furi_hal_resource_lease_release(h,FURI_HAL_LEASE_PULSE_NONCONNECTOR));
        REQUIRE(furi_hal_resource_lease_release(h,masks[i]));
        REQUIRE(!furi_hal_resource_lease_release(h,masks[i]));
    }
    uint32_t a=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_MONITOR_PC0);
    REQUIRE(a);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_PC0)==0U);
    REQUIRE(furi_hal_resource_lease_release(a,FURI_HAL_LEASE_MONITOR_PC0));
    a=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_I2C3_EXT);
    REQUIRE(a);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_PC0)==0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_PC1)==0U);
    REQUIRE(furi_hal_resource_lease_release(a,FURI_HAL_LEASE_I2C3_EXT));
    a=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_ONEWIRE_PA4);
    REQUIRE(a);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_PA4)==0U);
    REQUIRE(furi_hal_resource_lease_release(a,FURI_HAL_LEASE_ONEWIRE_PA4));
    a=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PC1);
    REQUIRE(a);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_PC1)==0U);
    REQUIRE(furi_hal_resource_lease_release(a,FURI_HAL_LEASE_IRQ_PC1));
    a=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_PC3);
    REQUIRE(a);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_PB3)==0U);
    REQUIRE(furi_hal_resource_lease_release(a,FURI_HAL_LEASE_PULSE_PC3));
    a=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_NONCONNECTOR);
    REQUIRE(a);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_PC0)==0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3)==0U);
    REQUIRE(furi_hal_resource_lease_release(a,FURI_HAL_LEASE_PULSE_NONCONNECTOR));
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_PC0|
        FURI_HAL_LEASE_PULSE_PC1)==0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_CORE|
        (1UL<<30))==0U);
    puts("E11 REAL FIRMWARE LEASE C PASS: 8 pulse composites, PC3/PB3 EXTI alias, TIM2 DMA and OneWire/I2C.");
    return 0;
}
'''
PRE=r'''
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
static pthread_mutex_t critical=PTHREAD_MUTEX_INITIALIZER;
#define FURI_CRITICAL_ENTER() do{if(pthread_mutex_lock(&critical))abort();}while(0)
#define FURI_CRITICAL_EXIT() do{if(pthread_mutex_unlock(&critical))abort();}while(0)
'''
def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("momentum_root",type=Path)
    a=ap.parse_args()
    root=a.momentum_root.resolve()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    s=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    start=h.index("enum {\n    FuriHalLeaseTim1")
    end=h.index("/* Returns unique nonzero",start)
    masks=h[start:end]
    source_start=s.index("/* Firmware-owned E11 lease primitive")
    source_end=s.index("const GpioPinRecord* furi_hal_resources_pin_by_number",source_start)
    implementation=s[source_start:source_end]
    assert "FURI_HAL_LEASE_PULSE_NONCONNECTOR" in masks
    assert "mask == FURI_HAL_LEASE_PULSE_PA7" in implementation
    with tempfile.TemporaryDirectory(prefix="labmate_e11_native_mask_") as td:
        c=Path(td)/"lease.c"
        exe=Path(td)/"lease"
        c.write_text(PRE+masks+implementation+RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-pthread",str(c),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
if __name__=="__main__": main()
