#pragma once
/* Phase3C: strict, PURE-C admission of one real Pulse IRQ pair at STOP.
 * A coherent native IRQ audit MUST be copied while interrupts are excluded.
 * This predicate does not observe GPIO, tear down leases, or publish evidence.
 */
#include "labmate_pulse_pair_audit.h"

typedef struct {
    LabMatePulsePairObservation pair;
    uint32_t start_tick;
    uint32_t stop_tick;
    uint32_t last_edge_tick;
    uint32_t start_tick_hz;
    uint32_t stop_tick_hz;
    uint32_t start_clock_hz;
    uint32_t stop_clock_hz;
    bool native_owner_confirmed;
    bool irq_active;
    bool timebase_enabled;
    bool release_fault;
} LabMateDoctorPulseCandidate;

/* Do not infer NO SIGNAL. Only fresh, non-overflowed complete paired
 * publications recorded during the correct native capture epoch may pass.
 * A valid candidate is still NOT a sealed reading until STOP releases E11.
 */
bool labmate_doctor_pulse_policy_accept(const LabMateDoctorPulseCandidate* candidate);
