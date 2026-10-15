#!/usr/bin/env python3
"""Host exercise of the EXACT firmware lease C SOURCE_INSERT, not a reimplementation.

Extract the C implementation from the fail-closed pinned firmware patcher,
compile it with pthread-backed critical-section stubs, stress release,
alias semantics, stale handles, full table, and 24-thread contested claims.
NO firmware compilation, USB, SD mutation or physical electrical tests.
"""
from __future__ import annotations
from pathlib import Path
import importlib.util
import subprocess
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "scripts/patch_momentum_resource_lease.py"
spec = importlib.util.spec_from_file_location("resource_lease_patch", PATCH)
assert spec and spec.loader
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)

assert patch.SOURCE_INSERT.count(patch.SOURCE_NEEDLE) == 1
assert patch.HEADER_INSERT.count(patch.HEADER_NEEDLE) == 1
source_c = patch.SOURCE_INSERT.split(patch.SOURCE_NEEDLE)[0]
header_c = patch.HEADER_INSERT.split(patch.HEADER_NEEDLE)[0]
assert "furi_hal_resource_lease_try_acquire" in source_c
assert "furi_hal_resource_lease_release" in source_c

PRELUDE = r'''
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
static pthread_mutex_t firmware_critical = PTHREAD_MUTEX_INITIALIZER;
#define FURI_CRITICAL_ENTER() do { if(pthread_mutex_lock(&firmware_critical)) abort(); } while(0)
#define FURI_CRITICAL_EXIT() do { if(pthread_mutex_unlock(&firmware_critical)) abort(); } while(0)
'''

TESTS = r'''
#define REQUIRE(cond) do { if(!(cond)) { \
    fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#cond);exit(1); } } while(0)

static void test_masks_and_stale_handles(void) {
    REQUIRE(furi_hal_resource_lease_try_acquire(0U) == 0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FuriHalLeaseTim1) == 0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(1UL << 31) == 0U);
    uint32_t a = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7);
    REQUIRE(a != 0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7) == 0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FuriHalLeasePa7) == 0U);
    uint32_t b = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3);
    REQUIRE(b != 0U && b != a);
    REQUIRE(!furi_hal_resource_lease_release(a, FURI_HAL_LEASE_COUNTER_PB3));
    REQUIRE(!furi_hal_resource_lease_release(a+1U, FURI_HAL_LEASE_PWM_PA7));
    REQUIRE(!furi_hal_resource_lease_release(0U, FURI_HAL_LEASE_PWM_PA7));
    REQUIRE(furi_hal_resource_lease_release(a, FURI_HAL_LEASE_PWM_PA7));
    REQUIRE(!furi_hal_resource_lease_release(a, FURI_HAL_LEASE_PWM_PA7));
    uint32_t c = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7);
    REQUIRE(c != 0U && c != a);
    REQUIRE(!furi_hal_resource_lease_release(a, FURI_HAL_LEASE_PWM_PA7));
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7) == 0U);
    REQUIRE(furi_hal_resource_lease_release(c, FURI_HAL_LEASE_PWM_PA7));
    REQUIRE(furi_hal_resource_lease_release(b, FURI_HAL_LEASE_COUNTER_PB3));
}

static void test_alias_and_capacity(void) {
    uint32_t button = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PC1);
    REQUIRE(button);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_I2C3_EXT) == 0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PC1) == 0U);
    uint32_t one_wire = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_ONEWIRE_PA4);
    REQUIRE(one_wire);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PA4) == 0U);
    REQUIRE(furi_hal_resource_lease_release(one_wire, FURI_HAL_LEASE_ONEWIRE_PA4));
    REQUIRE(furi_hal_resource_lease_release(button, FURI_HAL_LEASE_IRQ_PC1));

    /* The fixed table may fill with claims on disjoint physical resources.
     * Repeated mask conflicts must never consume a slot. */
    uint32_t i2c = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_I2C3_EXT);
    uint32_t counter = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3);
    uint32_t pwm = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7);
    REQUIRE(i2c && counter && pwm);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PC0) == 0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PC1) == 0U);
    REQUIRE(furi_hal_resource_lease_release(i2c, FURI_HAL_LEASE_I2C3_EXT));
    REQUIRE(furi_hal_resource_lease_release(counter, FURI_HAL_LEASE_COUNTER_PB3));
    REQUIRE(furi_hal_resource_lease_release(pwm, FURI_HAL_LEASE_PWM_PA7));
}

#define NTHREADS 24
typedef struct { pthread_barrier_t* barrier; uint32_t granted; } Worker;
static void* compete(void* opaque) {
    Worker* worker = opaque;
    int rc = pthread_barrier_wait(worker->barrier);
    if(rc != 0 && rc != PTHREAD_BARRIER_SERIAL_THREAD) abort();
    worker->granted = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3);
    return NULL;
}
static void test_real_source_race(void) {
    for(unsigned round=0;round<25;round++) {
        pthread_barrier_t barrier;
        REQUIRE(pthread_barrier_init(&barrier,NULL,NTHREADS+1)==0);
        pthread_t threads[NTHREADS];
        Worker workers[NTHREADS]={0};
        for(unsigned i=0;i<NTHREADS;i++) {
            workers[i].barrier=&barrier;
            REQUIRE(pthread_create(&threads[i],NULL,compete,&workers[i])==0);
        }
        int rc=pthread_barrier_wait(&barrier);
        REQUIRE(rc==0 || rc==PTHREAD_BARRIER_SERIAL_THREAD);
        unsigned winners=0;
        uint32_t winner=0;
        for(unsigned i=0;i<NTHREADS;i++) {
            REQUIRE(pthread_join(threads[i],NULL)==0);
            if(workers[i].granted) { winners++;winner=workers[i].granted; }
        }
        REQUIRE(winners==1);
        REQUIRE(furi_hal_resource_lease_release(winner,FURI_HAL_LEASE_COUNTER_PB3));
        REQUIRE(pthread_barrier_destroy(&barrier)==0);
    }
}

static void test_generation_exhaustion(void) {
    /* Private firmware-static state is visible in this exact-source TU. */
    REQUIRE(furi_hal_lease_used==0U);
    furi_hal_lease_last_handle=UINT32_MAX;
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7)==0U);
    REQUIRE(furi_hal_lease_used==0U);
}

int main(void) {
    test_masks_and_stale_handles();
    test_alias_and_capacity();
    test_real_source_race();
    test_generation_exhaustion();
    puts("E11.1a ACTUAL FIRMWARE LEASE C SOURCE HOST TEST PASS");
    puts("STILL NOT HAL/SERVICE ENFORCEMENT OR PHYSICAL DEVICE PASS");
    return 0;
}
'''

def main() -> None:
    with tempfile.TemporaryDirectory(prefix="labmate_e11_lease_") as tmp:
        cfile = Path(tmp) / "lease_runtime.c"
        exe = Path(tmp) / "lease_runtime"
        cfile.write_text(PRELUDE + header_c + source_c + TESTS)
        subprocess.run(
            ["gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
             "-pthread", str(cfile), "-o", str(exe)],
            check=True,
        )
        subprocess.run([str(exe)], check=True)

if __name__ == "__main__":
    main()
