#pragma once

#include <stdint.h>

/* TIM2/PB3 edge-counter estimator: pure math, no GPIO or hardware access.
 * A 100 ms window containing one edge must never be called "10 Hz".
 * Accumulate at least 10 edges for fast updates, or wait about 2 seconds
 * for sparse edges. A sparse gate requires >=2 edges to give a reading.
 * uint32_t cycle subtraction wraps safely while gates stay under ~67 s
 * at Flipper's 64 MHz CPU clock.
 */
#define LABMATE_HIGH_GATE_TARGET_EDGES 10U
#define LABMATE_HIGH_GATE_MAX_SECONDS 2U
#define LABMATE_HIGH_GATE_MIN_EDGES 2U

typedef enum {
    LabMateHighGateWait,
    LabMateHighGateNoSample,
    LabMateHighGatePublish
} LabMateHighGateResult;

/* output_millihz is changed ONLY on LabMateHighGatePublish.
 * The caller advances its window origin on either non-WAIT result.
 */
LabMateHighGateResult labmate_high_gate_evaluate(
    uint32_t edges,
    uint32_t elapsed_cycles,
    uint32_t core_clock_hz,
    uint32_t* output_millihz);
