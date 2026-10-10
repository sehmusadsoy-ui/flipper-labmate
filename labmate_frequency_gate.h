#pragma once
#include <stdint.h>

/* TIM2/PB3 count-window estimator, independent of Flipper hardware.
 * The caller MUST anchor at an observed rising-edge count and evaluate
 * only on a subsequent rising-edge count, not at an arbitrary timer tick.
 * This avoids +/-1 edge phase bias from fixed two-second gates.
 *
 * A gate publishes once at least 32 additional edges have been observed
 * OR at least three seconds have passed since the first edge, provided
 * there were at least two additional edges. This lets a 1 Hz source
 * settle after ~3 seconds while retaining fast updates above ~320 Hz.
 *
 * All intermediate products use uint64_t. Subtraction of 32-bit DWT
 * cycle timestamps is wrap-safe for intervals shorter than ~67 seconds
 * at 64 MHz; physical signal loss re-arms the window before then.
 */
#define LABMATE_HIGH_GATE_TARGET_EDGES 32U
#define LABMATE_HIGH_GATE_SLOW_SECONDS 3U
#define LABMATE_HIGH_GATE_MIN_EDGES 2U

typedef enum {
    LabMateHighGateWait,
    LabMateHighGateNoSample,
    LabMateHighGatePublish
} LabMateHighGateResult;

/* output_millihz is only written on Publish.
 * App re-anchors at the current observed rising edge after a result.
 */
LabMateHighGateResult labmate_high_gate_evaluate(
    uint32_t edges,
    uint32_t elapsed_cycles,
    uint32_t core_clock_hz,
    uint32_t* output_millihz);

/* PC1 period-to-frequency conversion used by the app-thread estimator.
 * Preserve the existing 64-bit intermediate and nearest-millihertz rounding.
 * False leaves output untouched; IRQ capture and sample filtering stay in core.
 */
int labmate_low_period_to_millihz(
    uint32_t period_cycles, uint32_t core_clock_hz, uint32_t* output_millihz);
