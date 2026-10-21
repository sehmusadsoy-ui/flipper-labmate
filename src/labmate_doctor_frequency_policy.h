#pragma once
/* Phase 3D-A, pure app-thread PRE-STOP policy for real Frequency sources.
 * A passed candidate is NOT sealed evidence: native lease teardown and the
 * snapshot integrity gate must ALSO pass before a Doctor verdict is allowed.
 * No HAL, GPIO, timer access, ISR readers or filesystem in this module.
 */
#include <stdbool.h>
#include <stdint.h>

typedef enum {
    LabMateDoctorFrequencyLowPC1 = 0,
    LabMateDoctorFrequencyHighPB3,
} LabMateDoctorFrequencyPath;

typedef struct {
    LabMateDoctorFrequencyPath path;
    uint8_t pin_index;
    bool owned_active;
    bool source_clock_running;
    bool release_fault;
    bool hold;
    uint32_t start_tick;
    uint32_t last_publication_tick;
    uint32_t stop_tick;
    uint32_t start_tick_hz;
    uint32_t stop_tick_hz;
    uint32_t start_clock_hz;
    uint32_t stop_clock_hz;
    uint32_t irq_or_timer_edge_count;
    uint32_t publication_count;
    uint32_t frequency_millihz;
    uint32_t low_period_cycles;
    uint32_t low_mailbox_overwrites;
    bool low_mailbox_exhausted;
    uint32_t high_gate_edges;
    uint32_t high_gate_cycles;
    bool high_audit_exhausted;
} LabMateDoctorFrequencyCandidate;

/* Only completed, recent, source-proven publications pass. Recomputes
 * frequency from the native period/gate path, never from a UI/HOLD value.
 * Cumulative timer/counter rollover or missing same-epoch timestamps MUST
 * be vetoed by the native adapter before passing this candidate.
 */
bool labmate_doctor_frequency_policy_accept(const LabMateDoctorFrequencyCandidate* c);
