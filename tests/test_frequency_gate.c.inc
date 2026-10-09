/* Portable PB3/TIM2 sparse counter gate tests; not part of firmware FAP. */
#include "labmate_frequency_gate.h"

#include <assert.h>
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
    const LabMateHighGateResult result =
        labmate_high_gate_evaluate(edges, elapsed_cycles, CPU_HZ, &actual);
    assert(result == expected);
    if(result == LabMateHighGatePublish) {
        assert(actual == expected_millihz);
    } else {
        assert(actual == 0xA5A5A5A5U);
    }
}

static void check_1hz_sample_timeline(void) {
    /* 100 ms software polls observe one 1 Hz rising edge at ticks 3,13,23...
     * The old algorithm reported 10 Hz at each isolated detected edge.
     * Publish only after the gate has observed enough time and edges.
     */
    uint32_t origin_cycle = 0U;
    uint32_t origin_count = 0U;
    uint32_t count = 0U;
    uint32_t valid = 0U;
    for(uint32_t tick = 1U; tick <= 50U; ++tick) {
        if(tick == 3U || tick == 13U || tick == 23U ||
           tick == 33U || tick == 43U) ++count;
        const uint32_t cycle = tick * TENTH_SECOND;
        uint32_t value = 0U;
        const LabMateHighGateResult result =
            labmate_high_gate_evaluate(
                count - origin_count, cycle - origin_cycle, CPU_HZ, &value);
        if(result != LabMateHighGateWait) {
            origin_count = count;
            origin_cycle = cycle;
            if(result == LabMateHighGatePublish) {
                assert(value == 1000U); /* 1.00 Hz, never 10.00 Hz */
                ++valid;
            }
        }
    }
    assert(valid == 2U);
}

static void check_counter_and_cycle_wrap(void) {
    /* Hardware counter and DWT CYCCNT use unsigned modulo subtraction. */
    const uint32_t old_count = UINT32_MAX - 4U;
    const uint32_t new_count = 5U; /* 10 edges across TIM2 wrap */
    assert((uint32_t)(new_count - old_count) == 10U);
    const uint32_t old_cycle = UINT32_MAX - TENTH_SECOND + 1U;
    const uint32_t new_cycle = 0U; /* ~100 ms across CPU cycle wrap */
    assert((uint32_t)(new_cycle - old_cycle) == TENTH_SECOND);
    check_result(new_count - old_count, new_cycle - old_cycle,
                 LabMateHighGatePublish, 100000U);
}

int main(void) {
    check_result(1U, TENTH_SECOND, LabMateHighGateWait, 0U);
    check_result(0U, CPU_HZ * 2U, LabMateHighGateNoSample, 0U);
    check_result(1U, CPU_HZ * 2U, LabMateHighGateNoSample, 0U);
    check_result(2U, CPU_HZ * 2U, LabMateHighGatePublish, 1000U);
    check_result(4U, CPU_HZ * 2U, LabMateHighGatePublish, 2000U);
    check_result(10U, CPU_HZ, LabMateHighGatePublish, 10000U);
    check_result(10U, TENTH_SECOND, LabMateHighGatePublish, 100000U);
    check_result(100U, TENTH_SECOND, LabMateHighGatePublish, 1000000U);
    check_result(5000U, TENTH_SECOND, LabMateHighGatePublish, 50000000U);
    check_result(9U, CPU_HZ, LabMateHighGateWait, 0U);
    check_result(0U, 0U, LabMateHighGateWait, 0U);
    {
        uint32_t mhz = 123U;
        assert(labmate_high_gate_evaluate(2U, CPU_HZ * 2U, 0U, &mhz) ==
               LabMateHighGateWait);
        assert(mhz == 123U);
        assert(labmate_high_gate_evaluate(2U, CPU_HZ * 2U, CPU_HZ, 0) ==
               LabMateHighGateWait);
        assert(labmate_high_gate_evaluate(UINT32_MAX, TENTH_SECOND,
                                          CPU_HZ, &mhz) ==
               LabMateHighGateNoSample);
        assert(mhz == 123U);
    }
    check_1hz_sample_timeline();
    check_counter_and_cycle_wrap();
    puts("LabMate v1.6 PB3 adaptive counter gate: host tests passed");
    return 0;
}
