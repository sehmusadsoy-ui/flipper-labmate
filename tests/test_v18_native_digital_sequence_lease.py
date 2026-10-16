#!/usr/bin/env python3
"""E11 native DigitalSequence exact firmware C lease-mask and source checks.

Host tests, pinned real patched resource lease body, no device or install.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

PRE = r"""
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
RUN = r"""
#define REQUIRE(x) do {if(!(x)) {fprintf(stderr,"E11 DIGITAL TEST FAIL line %d: %s\n",__LINE__,#x);exit(1);}} while(0)
int main(void) {
    const uint32_t masks[8]={
        FURI_HAL_LEASE_DIGITAL_PC0,FURI_HAL_LEASE_DIGITAL_PC1,
        FURI_HAL_LEASE_DIGITAL_PC3,FURI_HAL_LEASE_DIGITAL_PB2,
        FURI_HAL_LEASE_DIGITAL_PB3,FURI_HAL_LEASE_DIGITAL_PA4,
        FURI_HAL_LEASE_DIGITAL_PA6,FURI_HAL_LEASE_DIGITAL_PA7
    };
    for(size_t i=0;i<8;i++) {
        const uint32_t h=furi_hal_resource_lease_try_acquire(masks[i]);
        REQUIRE(h!=0U);
        REQUIRE(furi_hal_resource_lease_try_acquire(masks[i])==0U);
        REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3)==0U);
        REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_NONCONNECTOR)==0U);
        REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_DIGITAL_NONCONNECTOR)==0U);
        REQUIRE(!furi_hal_resource_lease_release(h,FURI_HAL_LEASE_DIGITAL_NONCONNECTOR));
        REQUIRE(furi_hal_resource_lease_release(h,masks[i]));
        REQUIRE(!furi_hal_resource_lease_release(h,masks[i]));
        const uint32_t pin=i==0 ? FURI_HAL_LEASE_MONITOR_PC0 :
             i==1 ? FURI_HAL_LEASE_MONITOR_PC1 :
             i==2 ? FURI_HAL_LEASE_MONITOR_PC3 :
             i==3 ? FURI_HAL_LEASE_MONITOR_PB2 :
             i==4 ? FURI_HAL_LEASE_MONITOR_PB3 :
             i==5 ? FURI_HAL_LEASE_MONITOR_PA4 :
             i==6 ? FURI_HAL_LEASE_MONITOR_PA6 : FURI_HAL_LEASE_MONITOR_PA7;
        const uint32_t other=furi_hal_resource_lease_try_acquire(pin);
        REQUIRE(other!=0U);
        REQUIRE(furi_hal_resource_lease_try_acquire(masks[i])==0U);
        REQUIRE(furi_hal_resource_lease_release(other,pin));
    }
    uint32_t h=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_DIGITAL_NONCONNECTOR);
    REQUIRE(h);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3)==0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_PC0)==0U);
    REQUIRE(furi_hal_resource_lease_release(h,FURI_HAL_LEASE_DIGITAL_NONCONNECTOR));
    h=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_I2C3_EXT);
    REQUIRE(h);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_DIGITAL_PC0)==0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_DIGITAL_PC1)==0U);
    REQUIRE(furi_hal_resource_lease_release(h,FURI_HAL_LEASE_I2C3_EXT));
    REQUIRE(furi_hal_resource_lease_try_acquire(
        FURI_HAL_LEASE_DIGITAL_PC0|FURI_HAL_LEASE_DIGITAL_PC1)==0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(
        FURI_HAL_LEASE_DIGITAL_CORE|(1UL<<30))==0U);
    puts("E11 NATIVE DIGITAL REAL RESOURCE C HOST PASS: TIM2/DMA CH1+2, 8 GPIO aliases, denied overlap, stale/partial release.");
    return 0;
}
"""

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("momentum_root",type=Path)
    a=ap.parse_args()
    root=a.momentum_root.resolve()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    s=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    d=(root/"lib/digital_signal/digital_sequence.c").read_text()
    start=h.index("enum {\n    FuriHalLeaseTim1")
    end=h.index("/* Returns unique nonzero",start)
    masks=h[start:end]
    source_start=s.index("/* Firmware-owned E11 lease primitive")
    source_end=s.index("const GpioPinRecord* furi_hal_resources_pin_by_number",source_start)
    implementation=s[source_start:source_end]
    assert "mask == FURI_HAL_LEASE_DIGITAL_PA7" in implementation
    assert "FURI_HAL_LEASE_DIGITAL_NONCONNECTOR" in masks
    assert "/* LabMate E11 native DigitalSequence owner. */" in d
    assert d.index("digital_sequence_e11_claim(sequence)") < d.index(
        "furi_hal_gpio_init(sequence->gpio, GpioModeOutputPushPull")
    assert d.index("digital_sequence_e11_release(sequence)") > d.index(
        "digital_sequence_finish(sequence);")
    assert "if(!furi_hal_bus_is_enabled(FuriHalBusTIM2))" in d
    assert "sequence->e11_lease_fault = true;" in d
    with tempfile.TemporaryDirectory(prefix="labmate_e11_digital_") as td:
        c=Path(td)/"lease.c"
        exe=Path(td)/"lease"
        c.write_text(PRE+masks+implementation+RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-pthread",str(c),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)

if __name__=="__main__":
    main()
