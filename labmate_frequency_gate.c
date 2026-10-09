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

    /* Preserve ~100 ms response when many edges are present.
     * For sparse input, a two-second gate avoids the 1 edge / 0.1 s
     * quantization error previously displayed as 10 Hz for a 1 Hz source.
     */
    if(edges < LABMATE_HIGH_GATE_TARGET_EDGES &&
       (uint64_t)elapsed_cycles <
           (uint64_t)core_clock_hz * LABMATE_HIGH_GATE_MAX_SECONDS) {
        return LabMateHighGateWait;
    }

    if(edges < LABMATE_HIGH_GATE_MIN_EDGES) {
        return LabMateHighGateNoSample;
    }

    /* Check both multiplication and output width, never wrap a reading. */
    const uint64_t scaled_edges = (uint64_t)edges * 1000ULL;
    if(scaled_edges > (UINT64_MAX - elapsed_cycles / 2U) / core_clock_hz) {
        return LabMateHighGateNoSample;
    }

    const uint64_t result =
        (scaled_edges * core_clock_hz + elapsed_cycles / 2U) / elapsed_cycles;
    if(result == 0U || result > UINT32_MAX) {
        return LabMateHighGateNoSample;
    }

    *output_millihz = (uint32_t)result;
    return LabMateHighGatePublish;
}
