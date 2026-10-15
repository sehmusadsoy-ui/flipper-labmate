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
    uint32_t token;
    uint64_t mask;
} Claim;

typedef struct {
    pthread_mutex_t guard; /* HOST ONLY: firmware needs its own atomic primitive */
    Claim claims[MAX_CLAIMS];
    uint64_t used;
} LeaseMap;

static bool lease_init(LeaseMap* m) {
    memset(m, 0, sizeof(*m));
    return pthread_mutex_init(&m->guard, NULL) == 0;
}

static void lease_destroy(LeaseMap* m) {
    (void)pthread_mutex_destroy(&m->guard);
}

/* All-or-nothing, non-reentrant acquisition. Each token has one mask.
 * Callers must claim BEFORE changing GPIO/clock/EXTI configuration.
 * Return false without touching the resource or partially claiming bits. */
static bool lease_claim(LeaseMap* m, uint32_t token, uint64_t mask) {
    if(token == 0U || mask == 0U || (mask & ~VALID_MASK)) return false;
    if(pthread_mutex_lock(&m->guard) != 0) abort();
    bool granted = false;
    int free_slot = -1;
    bool token_exists = false;
    for(size_t i = 0; i < MAX_CLAIMS; i++) {
        if(m->claims[i].token == token) token_exists = true;
        if(free_slot < 0 && m->claims[i].token == 0U) free_slot = (int)i;
    }
    if(!token_exists && free_slot >= 0 && !(m->used & mask)) {
        m->claims[free_slot] = (Claim){.token = token, .mask = mask};
        m->used |= mask;
        granted = true;
    }
    if(pthread_mutex_unlock(&m->guard) != 0) abort();
    return granted;
}

/* Wrong owner and partial/extra mask must not free another device's pin.
 * Token lifetime/uniqueness is the caller's obligation in this prototype. */
static bool lease_release(LeaseMap* m, uint32_t token, uint64_t mask) {
    if(token == 0U || mask == 0U || (mask & ~VALID_MASK)) return false;
    if(pthread_mutex_lock(&m->guard) != 0) abort();
    bool released = false;
    for(size_t i = 0; i < MAX_CLAIMS; i++) {
        if(m->claims[i].token == token && m->claims[i].mask == mask) {
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
    REQUIRE(lease_claim(&m, 100, COUNT_PB3)); /* unrelated firmware user */
    const uint64_t before = m.used;
    REQUIRE(!lease_claim(&m, 1, COUNT_PB3)); /* LabMate: fail closed */
    REQUIRE(m.used == before);
    REQUIRE(!lease_release(&m, 1, COUNT_PB3));
    REQUIRE(m.used == before);
    REQUIRE(lease_release(&m, 100, COUNT_PB3));
    REQUIRE(lease_claim(&m, 1, COUNT_PB3));
    REQUIRE(lease_release(&m, 1, COUNT_PB3));
    REQUIRE(m.used == 0U);
    lease_destroy(&m);
}

static void test_alias_conflicts_and_nonconflicts(void) {
    LeaseMap m; REQUIRE(lease_init(&m));
    REQUIRE(lease_claim(&m, 1, PWM_PA7));
    REQUIRE(lease_claim(&m, 2, COUNT_PB3)); /* disjoint timer/pin */
    REQUIRE(lease_claim(&m, 3, BUTTON_PC1));
    REQUIRE(!lease_claim(&m, 4, PULSE_PC1)); /* same EXTI line / PC1 */
    REQUIRE(!lease_claim(&m, 5, I2C3_EXT));  /* I2C shares PC1 */
    REQUIRE(lease_claim(&m, 6, ONEWIRE_PA4));
    REQUIRE(lease_release(&m, 3, BUTTON_PC1));
    REQUIRE(lease_claim(&m, 5, I2C3_EXT));
    REQUIRE(!lease_claim(&m, 7, PULSE_PC0)); /* I2C owns PC0 */
    REQUIRE(lease_release(&m, 5, I2C3_EXT));
    REQUIRE(lease_claim(&m, 7, PULSE_PC0));
    REQUIRE(lease_release(&m, 7, PULSE_PC0));
    REQUIRE(lease_release(&m, 6, ONEWIRE_PA4));
    REQUIRE(lease_release(&m, 2, COUNT_PB3));
    REQUIRE(lease_release(&m, 1, PWM_PA7));
    REQUIRE(m.used == 0U);
    lease_destroy(&m);
}

static void test_no_partial_or_foreign_release(void) {
    LeaseMap m; REQUIRE(lease_init(&m));
    REQUIRE(!lease_claim(&m, 10, 0U));
    REQUIRE(!lease_claim(&m, 10, BIT(30)));
    REQUIRE(!lease_claim(&m, 0, PWM_PA7));
    REQUIRE(m.used == 0U);
    REQUIRE(lease_claim(&m, 10, PWM_PA7));
    REQUIRE(!lease_claim(&m, 10, COUNT_PB3)); /* token not reusable */
    REQUIRE(!lease_release(&m, 11, PWM_PA7));
    REQUIRE(!lease_release(&m, 10, BIT(RES_PA7))); /* partial */
    REQUIRE(!lease_release(&m, 10, PWM_PA7 | BIT(RES_PB3)));
    REQUIRE(m.used == PWM_PA7);
    REQUIRE(lease_release(&m, 10, PWM_PA7));
    REQUIRE(!lease_release(&m, 10, PWM_PA7)); /* stale second release */
    REQUIRE(m.used == 0U);
    lease_destroy(&m);
}

#define WORKERS 24
typedef struct {
    LeaseMap* map;
    pthread_barrier_t* barrier;
    int number;
    bool granted;
} Worker;

static void* race_claim(void* context) {
    Worker* w = context;
    int rc = pthread_barrier_wait(w->barrier);
    if(rc != 0 && rc != PTHREAD_BARRIER_SERIAL_THREAD) abort();
    w->granted = lease_claim(w->map, (uint32_t)w->number, COUNT_PB3);
    return NULL; /* winner deliberately holds until main releases */
}

static void test_concurrent_claims(void) {
    LeaseMap m; REQUIRE(lease_init(&m));
    pthread_barrier_t barrier;
    REQUIRE(pthread_barrier_init(&barrier, NULL, WORKERS + 1) == 0);
    Worker workers[WORKERS] = {0};
    pthread_t ids[WORKERS];
    for(int i = 0; i < WORKERS; i++) {
        workers[i] = (Worker){.map = &m, .barrier = &barrier, .number = i + 1};
        REQUIRE(pthread_create(&ids[i], NULL, race_claim, &workers[i]) == 0);
    }
    int rc = pthread_barrier_wait(&barrier);
    REQUIRE(rc == 0 || rc == PTHREAD_BARRIER_SERIAL_THREAD);
    int winners = 0;
    uint32_t owner = 0U;
    for(int i = 0; i < WORKERS; i++) {
        REQUIRE(pthread_join(ids[i], NULL) == 0);
        if(workers[i].granted) { ++winners; owner = (uint32_t)workers[i].number; }
    }
    REQUIRE(winners == 1); /* never double-owner when contested */
    REQUIRE(m.used == COUNT_PB3);
    REQUIRE(lease_release(&m, owner, COUNT_PB3));
    REQUIRE(m.used == 0U);
    REQUIRE(pthread_barrier_destroy(&barrier) == 0);
    lease_destroy(&m);
}

int main(void) {
    test_foreign_owner_refusal();
    test_alias_conflicts_and_nonconflicts();
    test_no_partial_or_foreign_release();
    for(int run = 0; run < 25; run++) test_concurrent_claims();
    puts("HOST LEASE MODEL PASS: all-or-nothing, owner-safe, alias-safe, contested 24-thread test x25");
    puts("FIRMWARE-GLOBAL OWNERSHIP: NOT IMPLEMENTED / NOT HARDWARE VERIFIED");
    return 0;
}
