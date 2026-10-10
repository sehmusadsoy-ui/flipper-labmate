#include "labmate_frequency_gate.h"
#include <stdint.h>

LabMateHighGateResult labmate_high_gate_evaluate(
    uint32_t edges,
    uint32_t elapsed_cycles,
    uint32_t core_clock_hz,
    uint32_t* output_millihz) {
    if(output_millihz == 0 || core_clock_hz == 0U || elapsed_cycles == 0U) {
        return LabMateHighGateWait;
    }

    /* Edges and elapsed time MUST share the same observed-edge anchor.
     * The app evaluates this only when a new count edge is observed:
     * a 1 Hz source counted in a fixed 2 s bin could otherwise return
     * 3 / 2 Hz, i.e. 1.5 Hz, depending on gate phase.
     */
    if(edges < LABMATE_HIGH_GATE_TARGET_EDGES &&
       (uint64_t)elapsed_cycles <
           (uint64_t)core_clock_hz * LABMATE_HIGH_GATE_SLOW_SECONDS) {
        return LabMateHighGateWait;
    }
    if(edges < LABMATE_HIGH_GATE_MIN_EDGES) {
        return LabMateHighGateNoSample;
    }

    const uint64_t scaled_edges = (uint64_t)edges * 1000ULL;
    if(scaled_edges >
       (UINT64_MAX - (uint64_t)elapsed_cycles / 2ULL) / core_clock_hz) {
        return LabMateHighGateNoSample;
    }

    const uint64_t millihz =
        (scaled_edges * core_clock_hz + elapsed_cycles / 2ULL) / elapsed_cycles;
    if(millihz == 0ULL || millihz > UINT32_MAX) {
        return LabMateHighGateNoSample;
    }

    *output_millihz = (uint32_t)millihz;
    return LabMateHighGatePublish;
}

int labmate_low_period_to_millihz(
    uint32_t period_cycles, uint32_t core_clock_hz, uint32_t* output_millihz) {
    if(period_cycles == 0U || core_clock_hz == 0U || output_millihz == 0) return 0;
    *output_millihz = (uint32_t)(
        (((uint64_t)core_clock_hz * 1000ULL) + (period_cycles / 2U)) /
        period_cycles);
    return 1;
}
