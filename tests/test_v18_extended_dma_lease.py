#!/usr/bin/env python3
"""Compile actual firmware V1+V2 allocator C for cross-ABI resource conflicts.

Dormant V2 masks reserve SignalReader TIM16+DMAMUX+DMA2 CH2/3/5 and
external CC1101 TX TIM17+DMA2 CH3/4/5; no driver migration inferred.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

C_HEADER=r"""
#define _XOPEN_SOURCE 700
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#include <pthread.h>
static pthread_mutex_t critical=PTHREAD_MUTEX_INITIALIZER;
#define FURI_CRITICAL_ENTER() do {if(pthread_mutex_lock(&critical))abort();}while(0)
#define FURI_CRITICAL_EXIT() do {if(pthread_mutex_unlock(&critical))abort();}while(0)
"""
TEST=r"""
#define CHECK(cond) do {if(!(cond)){fprintf(stderr,"E11 V2 check failed line %d\n",__LINE__);abort();}}while(0)
static pthread_barrier_t barrier;
static uint32_t concurrent_success;
static void* racer(void* ptr) {
 (void)ptr;
 pthread_barrier_wait(&barrier);
 uint32_t lease=furi_hal_resource_lease_v2_try_acquire(FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX);
 if(lease) __atomic_add_fetch(&concurrent_success,1U,__ATOMIC_RELAXED);
 pthread_barrier_wait(&barrier);
 if(lease) CHECK(furi_hal_resource_lease_v2_release(lease,FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX));
 return NULL;
}
int main(void) {
 const uint64_t signal=FURI_HAL_LEASE_NATIVE_SIGNAL_READER_NFC;
 const uint64_t ext=FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX;
 CHECK((signal>>32)!=0 && (ext>>32)!=0);
 CHECK(!furi_hal_resource_lease_v2_try_acquire(0));
 CHECK(!furi_hal_resource_lease_v2_try_acquire(FuriHalLeaseTim16));
 CHECK(!furi_hal_resource_lease_v2_try_acquire((uint64_t)FuriHalLeaseTim17));
 CHECK(!furi_hal_resource_lease_v2_try_acquire(signal&~FuriHalLeaseDmamuxRg0));
 /* A genuine legacy NFC IRQ lease excludes the V2 NFC transparent RX. */
 uint32_t n=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2);
 CHECK(n);
 CHECK(!furi_hal_resource_lease_v2_try_acquire(signal));
 CHECK(furi_hal_resource_lease_release(n,FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2));
 /* A native RFID DMA2 CH2 owner excludes the SignalReader path. */
 uint32_t r=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA);
 CHECK(r && !furi_hal_resource_lease_v2_try_acquire(signal));
 CHECK(furi_hal_resource_lease_release(r,FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA));
 /* V2 collision: SignalReader DMA CH3+CH5 versus external CC1101 TX. */
 uint32_t s=furi_hal_resource_lease_v2_try_acquire(signal);
 CHECK(s);
 CHECK(!furi_hal_resource_lease_v2_try_acquire(signal));
 CHECK(!furi_hal_resource_lease_v2_try_acquire(ext));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA));
 CHECK(!furi_hal_resource_lease_v2_release(s,ext));
 CHECK(!furi_hal_resource_lease_release(s,FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2));
 CHECK(furi_hal_resource_lease_v2_release(s,signal));
 CHECK(!furi_hal_resource_lease_v2_release(s,signal));
 CHECK(furi_hal_resource_lease_v2_try_acquire(ext));
 /* Release most recently acquired V2 handle; exact handle remains unique. */
 uint32_t e=0;
 for(size_t i=0;i<FURI_HAL_LEASE_V2_MAX_CLAIMS;i++) {
  if(furi_hal_lease_v2_claims[i].handle &&
     furi_hal_lease_v2_claims[i].mask==ext) e=furi_hal_lease_v2_claims[i].handle;
 }
 CHECK(e && furi_hal_resource_lease_v2_release(e,ext));
 /* Legacy TIM17 and PB2/EXTI2 exclusions before ext TX starts. */
 n=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_TIMERS);
 CHECK(n && !furi_hal_resource_lease_v2_try_acquire(ext));
 CHECK(furi_hal_resource_lease_release(n,FURI_HAL_LEASE_NATIVE_NFC_TIMERS));
 r=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX);
 CHECK(r && !furi_hal_resource_lease_v2_try_acquire(ext));
 CHECK(furi_hal_resource_lease_release(r,FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX));
 e=furi_hal_resource_lease_v2_try_acquire(ext);
 CHECK(e);
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_TIMERS));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX));
 CHECK(!furi_hal_resource_lease_v2_try_acquire(signal));
 CHECK(furi_hal_resource_lease_v2_release(e,ext));
 /* Both families share the same monotonically increasing handle domain. */
 uint32_t a=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_MONITOR_PA7);
 uint32_t b=furi_hal_resource_lease_v2_try_acquire(signal);
 CHECK(a && b && a!=b);
 CHECK(furi_hal_resource_lease_release(a,FURI_HAL_LEASE_MONITOR_PA7));
 CHECK(furi_hal_resource_lease_v2_release(b,signal));
 /* Contended v2 claims of the same DMA/timer mask are atomic. */
 CHECK(!pthread_barrier_init(&barrier,NULL,8));
 pthread_t th[8];
 for(size_t i=0;i<8;i++)CHECK(!pthread_create(&th[i],NULL,racer,NULL));
 for(size_t i=0;i<8;i++)CHECK(!pthread_join(th[i],NULL));
 CHECK(!pthread_barrier_destroy(&barrier));
 CHECK(concurrent_success==1U);
 /* Handle wrap stays fail-closed for BOTH interfaces, not recycled. */
 furi_hal_lease_last_handle=UINT32_MAX;
 CHECK(!furi_hal_resource_lease_v2_try_acquire(signal));
 CHECK(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_MONITOR_PA7));
 CHECK(furi_hal_lease_used==0 && furi_hal_lease_used_hi==0);
 puts("E11 real V1+V2 lease production C atomic masks/cross-ABI/race PASS");
 return 0;
}
"""

def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    r=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    api=(root/"targets/f7/api_symbols.csv").read_text()
    mark="/* E11 additive 64-bit lease V2: no V1 ABI migration."
    assert mark in r
    assert "FURI_HAL_RESOURCE_LEASE_API_V2 1" in h
    assert "Function,+,furi_hal_resource_lease_v2_try_acquire,uint32_t,uint64_t" in api
    assert 'Function,+,furi_hal_resource_lease_v2_release,_Bool,"uint32_t, uint64_t"' in api
    assert "uint32_t furi_hal_resource_lease_try_acquire(uint32_t resources)" in r
    assert "bool furi_hal_resource_lease_release(uint32_t handle, uint32_t resources)" in r
    assert "uint32_t furi_hal_resource_lease_v2_try_acquire(uint64_t resources)" in r
    mask=h[h.index("enum {\n    FuriHalLeaseTim1"):h.index("/* Returns unique nonzero")]
    # The original V1 header slice already includes the added V2 masks.\n    alloc=r[r.index("/* Firmware-owned E11 lease primitive"):
            r.index("const GpioPinRecord* furi_hal_resources_pin_by_number")]
    with tempfile.TemporaryDirectory(prefix="e11_mask_v2_") as tmp:
        d=Path(tmp);exe=d/"lease"
        (d/"lease.c").write_text(C_HEADER+"\n"+mask+"\n"+alloc+"\n"+TEST)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                        "-pedantic","-pthread",str(d/"lease.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 V2 RESOURCE EXTENSION original C host PASS; DRIVER CLIENTS NOT MIGRATED")

if __name__=="__main__":
    main()
