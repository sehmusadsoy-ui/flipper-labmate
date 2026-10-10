/* Portable TIM2/PB3 observed-edge gate tests; NOT built into the FAP. */
#include "labmate_frequency_gate.h"
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#define CPU_HZ 64000000U
#define TENTH_SECOND (CPU_HZ / 10U)

static void check_result(
    uint32_t edges,
    uint32_t elapsed_cycles,
    LabMateHighGateResult expected,
    uint32_t expected_millihz) {
    uint32_t actual = 0xA5A5A5A5U;
    LabMateHighGateResult result =
        labmate_high_gate_evaluate(edges, elapsed_cycles, CPU_HZ, &actual);
    assert(result == expected);
    if(result == LabMateHighGatePublish) {
        assert(actual == expected_millihz);
    } else {
        assert(actual == 0xA5A5A5A5U);
    }
}

/* Simulate 100 ms TIM2 polls. Count exactly one rising edge each period_ticks
 * (1 Hz = 10; 2 Hz = 5; 10 Hz = 1). Estimation is invoked ONLY after a new
 * observed edge, and the origin is the first such observed edge.
 */
static void check_periodic_signal(uint32_t period_ticks, uint32_t expected_millihz) {
    uint32_t origin_cycle = 0U;
    uint32_t origin_count = 0U;
    uint32_t count = 0U;
    uint32_t publications = 0U;
    bool armed = false;
    for(uint32_t tick = 1U; tick <= 150U; ++tick) {
        if(tick < 3U || ((tick - 3U) % period_ticks) != 0U) continue;
        ++count;
        const uint32_t cycle = tick * TENTH_SECOND;
        if(!armed) {
            origin_cycle = cycle;
            origin_count = count;
            armed = true;
            continue;
        }
        uint32_t result_millihz = 0U;
        const LabMateHighGateResult result = labmate_high_gate_evaluate(
            count - origin_count, cycle - origin_cycle, CPU_HZ, &result_millihz);
        if(result != LabMateHighGateWait) {
            assert(result == LabMateHighGatePublish);
            /* Poll clock quantization cannot affect exact test ticks. */
            assert(result_millihz == expected_millihz);
            origin_cycle = cycle;
            origin_count = count;
            ++publications;
        }
    }
    assert(publications >= 2U);
}

static void check_irregular_counter_sampling(void) {
    /* A 1 Hz signal observed at 0.3, 1.3, 2.3, 3.4 seconds
     * must be near 1 Hz (3/3.1), not a 1.5 Hz fixed-gate artefact.
     */
    check_result(3U, 31U * TENTH_SECOND,
                 LabMateHighGatePublish, 968U);
}

static void check_counter_and_cycle_wrap(void) {
    const uint32_t old_count = UINT32_MAX - 25U;
    const uint32_t new_count = 6U; /* 32 TIM2 edges across wrap */
    assert((uint32_t)(new_count - old_count) == 32U);
    const uint32_t old_cycle = UINT32_MAX - TENTH_SECOND + 1U;
    const uint32_t new_cycle = 0U;
    assert((uint32_t)(new_cycle - old_cycle) == TENTH_SECOND);
    check_result(new_count - old_count, new_cycle - old_cycle,
                 LabMateHighGatePublish, 320000U);
}

static void check_low_period_conversion(void) {
    uint32_t measured = 777U;
    assert(labmate_low_period_to_millihz(64000000U, CPU_HZ, &measured));
    assert(measured == 1000U); /* 1 Hz */
    assert(labmate_low_period_to_millihz(6400000U, CPU_HZ, &measured));
    assert(measured == 10000U); /* 10 Hz */
    assert(labmate_low_period_to_millihz(640000U, CPU_HZ, &measured));
    assert(measured == 100000U); /* 100 Hz */
    assert(labmate_low_period_to_millihz(64000U, CPU_HZ, &measured));
    assert(measured == 1000000U); /* 1 kHz */
    assert(labmate_low_period_to_millihz(3U, 1U, &measured));
    assert(measured == 333U); /* nearest millihertz */
    assert(!labmate_low_period_to_millihz(0U, CPU_HZ, &measured));
    assert(!labmate_low_period_to_millihz(1U, 0U, &measured));
    assert(!labmate_low_period_to_millihz(1U, CPU_HZ, 0));
    assert(measured == 333U); /* invalid inputs must not overwrite */
}

int main(void) {
    check_low_period_conversion();
    /* An isolated edge can never produce a fake 10 Hz reading. */
    check_result(1U, TENTH_SECOND, LabMateHighGateWait, 0U);
    check_result(0U, CPU_HZ * 3U, LabMateHighGateNoSample, 0U);
    check_result(1U, CPU_HZ * 3U, LabMateHighGateNoSample, 0U);

    check_result(3U, CPU_HZ * 3U, LabMateHighGatePublish, 1000U);
    check_result(6U, CPU_HZ * 3U, LabMateHighGatePublish, 2000U);
    check_result(32U, CPU_HZ * 3U + TENTH_SECOND * 2U,
                 LabMateHighGatePublish, 10000U);
    check_result(32U, CPU_HZ / 3U, LabMateHighGatePublish, 96000U);
    check_result(32U, TENTH_SECOND, LabMateHighGatePublish, 320000U);
    check_result(5000U, TENTH_SECOND, LabMateHighGatePublish, 50000000U);
    check_result(3U, CPU_HZ, LabMateHighGateWait, 0U);
    check_result(0U, 0U, LabMateHighGateWait, 0U);
    {
        uint32_t mhz = 123U;
        assert(labmate_high_gate_evaluate(2U, CPU_HZ * 3U, 0U, &mhz) ==
               LabMateHighGateWait);
        assert(labmate_high_gate_evaluate(2U, CPU_HZ * 3U,
                                         CPU_HZ, 0) == LabMateHighGateWait);
        assert(labmate_high_gate_evaluate(UINT32_MAX,
                                          TENTH_SECOND, CPU_HZ, &mhz) ==
               LabMateHighGateNoSample);
        assert(mhz == 123U);
    }
    check_periodic_signal(10U, 1000U);
    check_periodic_signal(5U, 2000U);
    check_periodic_signal(1U, 10000U);
    check_irregular_counter_sampling();
    check_counter_and_cycle_wrap();
    puts("LabMate v1.6 PB3 edge-aligned counter gate: host tests passed");
    return 0;
}
