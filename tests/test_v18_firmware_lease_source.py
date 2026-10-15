#!/usr/bin/env python3
"""Execute the ACTUAL firmware E11.1a lease C functions under host locks.

Unlike tests/v18_firmware_lease_proto.c, this extracts the C source
emitted by patch_momentum_resource_lease.py and compiles it unchanged,
only replacing STM32 FURI_CRITICAL_ENTER/EXIT with a pthread mutex.
NO hardware/USB/SD writes, no firmware compilation claims.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "scripts/patch_momentum_resource_lease.py"


def main() -> None:
    spec = importlib.util.spec_from_file_location("labmate_e11_patch", PATCH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load exact source patch")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    header = mod.HEADER_INSERT.split(mod.HEADER_NEEDLE, 1)[0]
    source = mod.SOURCE_INSERT.split(mod.SOURCE_NEEDLE, 1)[0]
    if not header or not source or "furi_hal_resource_lease_release" not in source:
        raise RuntimeError("Firmware source extraction failed")
    if any(x in source for x in (
        "furi_hal_gpio_init", "LL_TIM_", "furi_hal_bus_enable",
        "furi_hal_pwm_start", "storage_file_", "furi_hal_power_"
    )):
        raise RuntimeError("Lease primitive must not change peripheral state")

    stub = r'''
#define _POSIX_C_SOURCE 200809L
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
static pthread_mutex_t firmware_irq_guard = PTHREAD_MUTEX_INITIALIZER;
#define FURI_CRITICAL_ENTER() do { if(pthread_mutex_lock(&firmware_irq_guard)) abort(); } while(0)
#define FURI_CRITICAL_EXIT() do { if(pthread_mutex_unlock(&firmware_irq_guard)) abort(); } while(0)
#define REQUIRE(x) do { if(!(x)) { fprintf(stderr,"FAIL %d: %s\n",__LINE__,#x); exit(1); } } while(0)
'''
    tests = r'''
static void basic_tests(void) {
    REQUIRE(furi_hal_resource_lease_try_acquire(0U) == 0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FuriHalLeaseTim1) == 0U);
    REQUIRE(furi_hal_resource_lease_try_acquire((1U << 30)) == 0U);
    uint32_t pwm = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7);
    REQUIRE(pwm != 0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7) == 0U);
    uint32_t tim2 = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3);
    REQUIRE(tim2 != 0U);
    uint32_t button = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PC1);
    REQUIRE(button != 0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PC1) == 0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_I2C3_EXT) == 0U);
    REQUIRE(!furi_hal_resource_lease_release(pwm + 123U, FURI_HAL_LEASE_PWM_PA7));
    REQUIRE(!furi_hal_resource_lease_release(pwm, FuriHalLeasePa7));
    REQUIRE(!furi_hal_resource_lease_release(pwm, FURI_HAL_LEASE_COUNTER_PB3));
    REQUIRE(furi_hal_resource_lease_release(button, FURI_HAL_LEASE_IRQ_PC1));
    uint32_t i2c = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_I2C3_EXT);
    REQUIRE(i2c != 0U);
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PC0) == 0U);
    REQUIRE(furi_hal_resource_lease_release(i2c, FURI_HAL_LEASE_I2C3_EXT));
    REQUIRE(furi_hal_resource_lease_release(tim2, FURI_HAL_LEASE_COUNTER_PB3));
    REQUIRE(furi_hal_resource_lease_release(pwm, FURI_HAL_LEASE_PWM_PA7));
    REQUIRE(!furi_hal_resource_lease_release(pwm, FURI_HAL_LEASE_PWM_PA7));
    uint32_t next = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7);
    REQUIRE(next != 0U && next != pwm);
    REQUIRE(!furi_hal_resource_lease_release(pwm, FURI_HAL_LEASE_PWM_PA7));
    REQUIRE(furi_hal_resource_lease_release(next, FURI_HAL_LEASE_PWM_PA7));
}
#define THREADS 24
typedef struct { pthread_barrier_t* gate; uint32_t owner; } Worker;
static void* thread_attempt(void* arg) {
    Worker* w = arg;
    int e = pthread_barrier_wait(w->gate);
    if(e != 0 && e != PTHREAD_BARRIER_SERIAL_THREAD) abort();
    w->owner = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3);
    return NULL;
}
static void contested_tests(void) {
    for(int run=0; run<25; ++run) {
        pthread_barrier_t gate;
        REQUIRE(pthread_barrier_init(&gate, NULL, THREADS+1) == 0);
        Worker w[THREADS] = {0};
        pthread_t t[THREADS];
        for(int i=0;i<THREADS;i++) {
            w[i].gate=&gate;
            REQUIRE(pthread_create(&t[i], NULL, thread_attempt, &w[i]) == 0);
        }
        int e = pthread_barrier_wait(&gate);
        REQUIRE(e == 0 || e == PTHREAD_BARRIER_SERIAL_THREAD);
        int winners = 0;
        uint32_t owner = 0U;
        for(int i=0;i<THREADS;i++) {
            REQUIRE(pthread_join(t[i], NULL) == 0);
            if(w[i].owner != 0U) { winners++; owner=w[i].owner; }
        }
        REQUIRE(winners == 1);
        REQUIRE(furi_hal_resource_lease_release(owner,FURI_HAL_LEASE_COUNTER_PB3));
        REQUIRE(pthread_barrier_destroy(&gate) == 0);
    }
}
int main(void) {
    basic_tests();
    contested_tests();
    furi_hal_lease_last_handle = UINT32_MAX;
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7) == 0U);
    puts("E11.1a ACTUAL FIRMWARE LEASE C SOURCE HOST HARNESS PASS: alias, stale handle, 24 threads x25, exhaustion");
    puts("NO HAL INTERPOSITION, NO PHYSICAL DEVICE");
    return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix="labmate-e11-firmware-") as temp:
        src = Path(temp) / "lease_host.c"
        exe = Path(temp) / "lease_host"
        src.write_text(stub + header + "\n" + source + "\n" + tests, encoding="utf-8")
        subprocess.run([
            "gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
            "-pthread", str(src), "-o", str(exe)
        ], check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    main()
