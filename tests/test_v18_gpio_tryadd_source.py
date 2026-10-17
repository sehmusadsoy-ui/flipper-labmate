#!/usr/bin/env python3
"""Compile/test the EXACT E11.1c firmware GPIO try-add C body (host only).

Does not simulate pin ownership, register configuration or real STM32 IRQs.
Tests nonasserting slot occupancy, invalid inputs and atomic contention.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "scripts/patch_momentum_gpio_tryadd.py"
spec = importlib.util.spec_from_file_location("e11_gpio_tryadd", PATCH)
assert spec and spec.loader
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
assert p.SOURCE_INSERT.count(p.SOURCE_NEEDLE) == 1
src = p.SOURCE_INSERT.split(p.SOURCE_NEEDLE)[0]
assert "furi_hal_gpio_try_add_int_callback" in src
assert "LL_EXTI_EnableIT_0_31" in src

PRELUDE = r'''
#define _POSIX_C_SOURCE 200809L
#include <pthread.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
typedef struct { uint32_t pin; } GpioPin;
typedef void (*GpioExtiCallback)(void*);
typedef struct { GpioExtiCallback callback; void* context; } Cb;
static Cb gpio_interrupt[16];
static pthread_mutex_t critical = PTHREAD_MUTEX_INITIALIZER;
static unsigned enables = 0U;
#define FURI_CRITICAL_ENTER() do { if(pthread_mutex_lock(&critical)) abort(); } while(0)
#define FURI_CRITICAL_EXIT() do { if(pthread_mutex_unlock(&critical)) abort(); } while(0)
#define GET_EXTI_LINE(pin) (pin)
static uint8_t furi_hal_gpio_get_pin_num(const GpioPin* gpio) {
    for(uint8_t i=0;i<16;i++) if(gpio->pin == (1UL<<i)) return i;
    abort();
}
static void LL_EXTI_EnableIT_0_31(uint32_t line) { (void)line; enables++; }
'''

TESTS = r'''
#define REQUIRE(cond) do { if(!(cond)) { \
    fprintf(stderr,"GPIO FAIL at line %d: %s\n",__LINE__,#cond); exit(1); \
} } while(0)
static void callback(void* ctx) { (void)ctx; }

static void test_basic(void) {
    GpioPin pc1={.pin=1UL<<1};
    GpioPin pb1={.pin=1UL<<1}; /* same shared EXTI line */
    REQUIRE(!furi_hal_gpio_try_add_int_callback(NULL, callback, NULL));
    REQUIRE(!furi_hal_gpio_try_add_int_callback(&pc1, NULL, NULL));
    REQUIRE(enables == 0U);
    REQUIRE(furi_hal_gpio_try_add_int_callback(&pc1, callback, &pc1));
    REQUIRE(enables == 1U);
    REQUIRE(gpio_interrupt[1].callback == callback);
    REQUIRE(gpio_interrupt[1].context == &pc1);
    REQUIRE(!furi_hal_gpio_try_add_int_callback(&pb1, callback, &pb1));
    REQUIRE(enables == 1U); /* refusal does not enable EXTI */
    REQUIRE(gpio_interrupt[1].context == &pc1); /* original owner untouched */
}

#define NTHREADS 24
typedef struct { pthread_barrier_t* barrier; bool ok; } Worker;
static void* compete(void* opaque) {
    Worker* w=opaque;
    GpioPin pin={.pin=1UL<<0};
    int rc=pthread_barrier_wait(w->barrier);
    if(rc!=0 && rc!=PTHREAD_BARRIER_SERIAL_THREAD) abort();
    w->ok=furi_hal_gpio_try_add_int_callback(&pin,callback,w);
    return NULL;
}
static void test_contention(void) {
    for(unsigned run=0;run<25;run++) {
        gpio_interrupt[0].callback=NULL;
        gpio_interrupt[0].context=NULL;
        const unsigned before=enables;
        pthread_barrier_t bar;
        REQUIRE(pthread_barrier_init(&bar,NULL,NTHREADS+1)==0);
        pthread_t threads[NTHREADS];
        Worker workers[NTHREADS]={0};
        for(unsigned i=0;i<NTHREADS;i++) {
            workers[i].barrier=&bar;
            REQUIRE(pthread_create(&threads[i],NULL,compete,&workers[i])==0);
        }
        int rc=pthread_barrier_wait(&bar);
        REQUIRE(rc==0 || rc==PTHREAD_BARRIER_SERIAL_THREAD);
        unsigned wins=0;
        for(unsigned i=0;i<NTHREADS;i++) {
            REQUIRE(pthread_join(threads[i],NULL)==0);
            if(workers[i].ok) wins++;
        }
        REQUIRE(wins==1);
        REQUIRE(enables==before+1);
        REQUIRE(gpio_interrupt[0].callback==callback);
        REQUIRE(pthread_barrier_destroy(&bar)==0);
    }
}

int main(void) {
    test_basic();
    test_contention();
    puts("E11.1c EXACT FIRMWARE GPIO TRY-ADD C HOST TEST PASS");
    puts("PIN MODE / REAL EXTI / CROSS-SERVICE GLOBAL OWNERSHIP: NOT VERIFIED");
    return 0;
}
'''

def main() -> None:
    with tempfile.TemporaryDirectory(prefix="labmate_exti_try_") as tmp:
        c = Path(tmp) / "firmware_gpio_tryadd.c"
        exe = Path(tmp) / "firmware_gpio_tryadd"
        c.write_text(PRELUDE + src + TESTS)
        subprocess.run(["gcc", "-std=c11", "-O2", "-Wall", "-Wextra",
                        "-Werror", "-pthread", str(c), "-o", str(exe)], check=True)
        subprocess.run([str(exe)], check=True)

if __name__ == "__main__":
    main()
