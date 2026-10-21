#pragma once
/* Phase 2I: app-thread audit of COMPLETED PB3/TIM2 high-frequency gates.
 * A 100-ms poll, pending WAIT, and NoSample are NOT published measurements.
 * No ISR, Furi HAL, GPIO/lease, clock reads, heap or storage dependency.
 */
#include "labmate_frequency_gate.h"
#include <stdbool.h>
#include <stdint.h>
#include <limits.h>

typedef struct {
    uint32_t publications;
    uint32_t last_counter;
    uint32_t last_gate_edges;
    uint32_t last_gate_cycles;
    uint32_t last_frequency_millihz;
    bool exhausted;
} LabMateHighGateAudit;

/* Reset ONLY after native TIM2 configure succeeded and before it is enabled.
 * Failed starts, HOLD, logger polls and a normal UI redraw MUST NOT reset it.
 */
static inline void labmate_high_gate_audit_reset(LabMateHighGateAudit* audit) {
    if(!audit) return;
    *audit = (LabMateHighGateAudit){0};
}

/* Called only after the ORIGINAL hardware gate evaluator returned a verdict.
 * Returns true ONLY when a genuine Publish has been admitted and accounted.
 * Do not infer period ticks from TIM2 poll rate or gate frequency.
 * A wrapped publication generation is permanently rejected until a new
 * independently leased capture epoch (not until a screen repaint).
 */
static inline bool labmate_high_gate_audit_record(
    LabMateHighGateAudit* audit, LabMateHighGateResult result,
    uint32_t hardware_counter, uint32_t gate_edges, uint32_t gate_cycles,
    uint32_t measured_frequency_millihz) {
    if(!audit || audit->exhausted || result != LabMateHighGatePublish) return false;
    if(gate_edges < LABMATE_HIGH_GATE_MIN_EDGES || gate_cycles == 0U ||
       measured_frequency_millihz == 0U) return false;
    if(audit->publications == UINT32_MAX) {
        audit->exhausted = true;
        return false;
    }
    if(audit->publications != 0U && hardware_counter == audit->last_counter) {
        /* No fresh hardware counter boundary can certify a new result. */
        return false;
    }
    ++audit->publications;
    audit->last_counter = hardware_counter;
    audit->last_gate_edges = gate_edges;
    audit->last_gate_cycles = gate_cycles;
    audit->last_frequency_millihz = measured_frequency_millihz;
    return true;
}
