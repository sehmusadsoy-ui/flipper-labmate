/* Pure-Pulse arithmetic host regression (no SDK/GPIO). */
#include "labmate_pulse_math.h"
#include <assert.h>
#include <stdio.h>
#include <stdint.h>

static void check(uint32_t high, uint32_t low, uint32_t period, uint32_t duty) {
    uint32_t p = 77U;
    uint32_t d = 88U;
    assert(labmate_pulse_period_and_duty(high, low, &p, &d));
    assert(p == period && d == duty);
}

int main(void) {
    check(500U, 500U, 1000U, 500U);
    check(250U, 750U, 1000U, 250U);
    check(750U, 250U, 1000U, 750U);
    check(1U, 2U, 3U, 333U);
    check(2U, 1U, 3U, 667U);
    check(0U, 1U, 1U, 0U);
    check(1U, 0U, 1U, 1000U);
    check(UINT32_MAX, 0U, UINT32_MAX, 1000U);

    uint32_t p = 101U, d = 202U;
    assert(!labmate_pulse_period_and_duty(0U, 0U, &p, &d));
    assert(p == 101U && d == 202U);
    assert(!labmate_pulse_period_and_duty(UINT32_MAX, 1U, &p, &d));
    assert(p == 101U && d == 202U);
    assert(!labmate_pulse_period_and_duty(2U, 2U, NULL, &d));
    assert(!labmate_pulse_period_and_duty(2U, 2U, &p, NULL));

    const uint32_t a[LABMATE_PULSE_MEDIAN_SAMPLES] = {5U,1U,4U,2U,3U};
    const uint32_t b[LABMATE_PULSE_MEDIAN_SAMPLES] = {9U,9U,2U,9U,0U};
    const uint32_t c[LABMATE_PULSE_MEDIAN_SAMPLES] = {UINT32_MAX,0U,3U,2U,4U};
    const uint32_t e[LABMATE_PULSE_MEDIAN_SAMPLES] = {7U,7U,7U,7U,7U};
    assert(labmate_pulse_median5(a) == 3U);
    assert(labmate_pulse_median5(b) == 9U);
    assert(labmate_pulse_median5(c) == 3U);
    assert(labmate_pulse_median5(e) == 7U);
    puts("LabMate v1.6.1 portable Pulse math PASS");
    return 0;
}
