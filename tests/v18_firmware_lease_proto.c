/* LabMate v1.8 firmware-wide lease DESIGN PROTOTYPE — HOST ONLY.
 *
 * This is NOT linked into the LabMate FAP or the Momentum HAL. pthread
 * emulates a tiny atomic firmware critical section for CI race testing.
 * It cannot protect device peripherals unless *all* relevant firmware
 * HAL entry points are integrated into a common, real lease.
 *
 * Build: cc -std=c11 -Wall -Wextra -Werror -pthread
 *        tests/v18_firmware_lease_proto.c -o /tmp/labmate-lease-proto
 */
#define _POSIX_C_SOURCE 200809L
#include <pthread.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BIT(n) (UINT64_C(1) << (n))
enum {
    RES_TIM1 = 0, RES_PA7,
    RES_TIM2, RES_PB3,
    RES_EXTI0, RES_PC0,
    RES_EXTI1, RES_PC1,
    RES_EXTI2, RES_PB2,
    RES_EXTI4, RES_PA4,
    RES_USART1, RES_PA9, RES_PA10,
    RES_I2C3
};
#define VALID_MASK (BIT(16) - 1U)
#define PWM_PA7     (BIT(RES_TIM1) | BIT(RES_PA7))
#define COUNT_PB3   (BIT(RES_TIM2) | BIT(RES_PB3))
#define BUTTON_PC1  (BIT(RES_EXTI1) | BIT(RES_PC1))
#define PULSE_PC1   (BIT(RES_EXTI1) | BIT(RES_PC1))
#define PULSE_PC0   (BIT(RES_EXTI0) | BIT(RES_PC0))
#define I2C3_EXT    (BIT(RES_I2C3) | BIT(RES_PC0) | BIT(RES_PC1))
#define ONEWIRE_PA4 (BIT(RES_PA4))
#define MAX_CLAIMS 32

typedef struct {
    uint64_t handle;
    uint64_t mask;
} Claim;

typedef struct {
    pthread_mutex_t guard; /* HOST ONLY: firmware needs its own atomic primitive */
    Claim claims[MAX_CLAIMS];
    uint64_t used;
    uint64_t last_handle; /* never reused within this map lifetime */
} LeaseMap;

static bool lease_init(LeaseMap* m) {
    memset(m, 0, sizeof(*m));
    return pthread_mutex_init(&m->guard, NULL) == 0;
}

static void lease_destroy(LeaseMap* m) {
    (void)pthread_mutex_destroy(&m->guard);
}

/* Return a new opaque nonzero lease handle, or zero on refusal.
 * Mint handles under the same lock as reservation; never recycle them.
 * Exhaustion FAILS CLOSED instead of wrapping into a stale handle.
 * Always claim BEFORE changing any GPIO/clock/EXTI registers. */
static uint64_t lease_claim(LeaseMap* m, uint64_t mask) {
    if(mask == 0U || (mask & ~VALID_MASK)) return 0U;
    if(pthread_mutex_lock(&m->guard) != 0) abort();
    uint64_t granted = 0U;
    int free_slot = -1;
    for(size_t i = 0; i < MAX_CLAIMS; i++) {
        if(free_slot < 0 && m->claims[i].handle == 0U) free_slot = (int)i;
    }
    if(free_slot >= 0 && !(m->used & mask) && m->last_handle != UINT64_MAX) {
        granted = ++m->last_handle;
        m->claims[free_slot] = (Claim){.handle = granted, .mask = mask};
        m->used |= mask;
    }
    if(pthread_mutex_unlock(&m->guard) != 0) abort();
    return granted;
}

/* Only an exact, active owner handle may release its exact mask.
 * An obsolete handle cannot release a later lease on the same pin. */
static bool lease_release(LeaseMap* m, uint64_t handle, uint64_t mask) {
    if(handle == 0U || mask == 0U || (mask & ~VALID_MASK)) return false;
    if(pthread_mutex_lock(&m->guard) != 0) abort();
    bool released = false;
    for(size_t i = 0; i < MAX_CLAIMS; i++) {
        if(m->claims[i].handle == handle && m->claims[i].mask == mask) {
            m->used &= ~mask;
            m->claims[i] = (Claim){0};
            released = true;
            break;
        }
    }
    if(pthread_mutex_unlock(&m->guard) != 0) abort();
    return released;
}

#define REQUIRE(cond) do { \
    if(!(cond)) { \
        fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #cond); \
        exit(1); \
    } \
} while(0)

static void test_foreign_owner_refusal(void) {
    LeaseMap m; REQUIRE(lease_init(&m));
    uint64_t foreign = lease_claim(&m, COUNT_PB3);
    REQUIRE(foreign != 0U); /* unrelated firmware service */
    const uint64_t before = m.used;
    REQUIRE(lease_claim(&m, COUNT_PB3) == 0U); /* LabMate fail closed */
    REQUIRE(m.used == before);
    REQUIRE(!lease_release(&m, foreign + 1U, COUNT_PB3));
    REQUIRE(m.used == before);
    REQUIRE(lease_release(&m, foreign, COUNT_PB3));
    uint64_t ours = lease_claim(&m, COUNT_PB3);
    REQUIRE(ours != 0U && ours != foreign);
    REQUIRE(!lease_release(&m, foreign, COUNT_PB3)); /* stale owner */
    REQUIRE(m.used == COUNT_PB3);
    REQUIRE(lease_release(&m, ours, COUNT_PB3));
    REQUIRE(m.used == 0U);
    lease_destroy(&m);
}

static void test_alias_conflicts_and_nonconflicts(void) {
    LeaseMap m; REQUIRE(lease_init(&m));
    uint64_t pwm = lease_claim(&m, PWM_PA7);
    uint64_t counter = lease_claim(&m, COUNT_PB3);
    uint64_t button = lease_claim(&m, BUTTON_PC1);
    REQUIRE(pwm && counter && button); /* disjoint timer/pin claims */
    REQUIRE(lease_claim(&m, PULSE_PC1) == 0U); /* same EXTI line / pin */
    REQUIRE(lease_claim(&m, I2C3_EXT) == 0U);  /* I2C also uses PC1 */
    uint64_t one_wire = lease_claim(&m, ONEWIRE_PA4);
    REQUIRE(one_wire);
    REQUIRE(lease_release(&m, button, BUTTON_PC1));
    uint64_t i2c = lease_claim(&m, I2C3_EXT);
    REQUIRE(i2c);
    REQUIRE(lease_claim(&m, PULSE_PC0) == 0U); /* I2C uses PC0 */
    REQUIRE(lease_release(&m, i2c, I2C3_EXT));
    uint64_t pulse = lease_claim(&m, PULSE_PC0);
    REQUIRE(pulse);
    REQUIRE(lease_release(&m, pulse, PULSE_PC0));
    REQUIRE(lease_release(&m, one_wire, ONEWIRE_PA4));
    REQUIRE(lease_release(&m, counter, COUNT_PB3));
    REQUIRE(lease_release(&m, pwm, PWM_PA7));
    REQUIRE(m.used == 0U);
    lease_destroy(&m);
}

static void test_invalid_wrong_and_stale_release(void) {
    LeaseMap m; REQUIRE(lease_init(&m));
    REQUIRE(lease_claim(&m, 0U) == 0U);
    REQUIRE(lease_claim(&m, BIT(30)) == 0U);
    REQUIRE(m.used == 0U);
    uint64_t first = lease_claim(&m, PWM_PA7);
    REQUIRE(first != 0U);
    REQUIRE(lease_claim(&m, PWM_PA7) == 0U);
    REQUIRE(!lease_release(&m, first + 100U, PWM_PA7));
    REQUIRE(!lease_release(&m, first, BIT(RES_PA7)));
    REQUIRE(!lease_release(&m, first, PWM_PA7 | BIT(RES_PB3)));
    REQUIRE(m.used == PWM_PA7);
    REQUIRE(lease_release(&m, first, PWM_PA7));
    REQUIRE(!lease_release(&m, first, PWM_PA7));
    uint64_t second = lease_claim(&m, PWM_PA7);
    REQUIRE(second != 0U && second != first);
    REQUIRE(!lease_release(&m, first, PWM_PA7)); /* stale handle */
    REQUIRE(m.used == PWM_PA7);
    REQUIRE(lease_release(&m, second, PWM_PA7));
    REQUIRE(m.used == 0U);
    m.last_handle = UINT64_MAX; /* simulate exhaustion */
    REQUIRE(lease_claim(&m, COUNT_PB3) == 0U);
    REQUIRE(m.used == 0U);
    lease_destroy(&m);
}

#define WORKERS 24
typedef struct {
    LeaseMap* map;
    pthread_barrier_t* barrier;
    uint64_t granted;
} Worker;

static void* race_claim(void* context) {
    Worker* w = context;
    int rc = pthread_barrier_wait(w->barrier);
    if(rc != 0 && rc != PTHREAD_BARRIER_SERIAL_THREAD) abort();
    w->granted = lease_claim(w->map, COUNT_PB3);
    return NULL; /* winner holds until main releases */
}

static void test_concurrent_claims(void) {
    LeaseMap m; REQUIRE(lease_init(&m));
    pthread_barrier_t barrier;
    REQUIRE(pthread_barrier_init(&barrier, NULL, WORKERS + 1) == 0);
    Worker workers[WORKERS] = {0};
    pthread_t ids[WORKERS];
    for(int i = 0; i < WORKERS; i++) {
        workers[i] = (Worker){.map = &m, .barrier = &barrier};
        REQUIRE(pthread_create(&ids[i], NULL, race_claim, &workers[i]) == 0);
    }
    int rc = pthread_barrier_wait(&barrier);
    REQUIRE(rc == 0 || rc == PTHREAD_BARRIER_SERIAL_THREAD);
    int winners = 0;
    uint64_t handle = 0U;
    for(int i = 0; i < WORKERS; i++) {
        REQUIRE(pthread_join(ids[i], NULL) == 0);
        if(workers[i].granted) { ++winners; handle = workers[i].granted; }
    }
    REQUIRE(winners == 1);
    REQUIRE(m.used == COUNT_PB3);
    REQUIRE(lease_release(&m, handle, COUNT_PB3));
    REQUIRE(m.used == 0U);
    REQUIRE(pthread_barrier_destroy(&barrier) == 0);
    lease_destroy(&m);
}

int main(void) {
    test_foreign_owner_refusal();
    test_alias_conflicts_and_nonconflicts();
    test_invalid_wrong_and_stale_release();
    for(int run = 0; run < 25; run++) test_concurrent_claims();
    puts("HOST LEASE MODEL PASS: atomic all-or-nothing, stale-handle-safe, alias-safe, 24-thread contest x25");
    puts("FIRMWARE-GLOBAL OWNERSHIP: NOT IMPLEMENTED / NOT HARDWARE VERIFIED");
    return 0;
}
