#pragma once
/* Phase 2C: app-thread record of explicitly confirmed capture transitions.
 * Not an IRQ callback, firmware lease API, or substitute for physical proof.
 * The caller must provide REAL completed-sample and teardown observations.
 */
#include "labmate_snapshot_bridge.h"

typedef enum {
    LabMateEvidenceIdle = 0,
    LabMateEvidenceCapturing,
    LabMateEvidenceSealed,
    LabMateEvidenceReleaseFault,
} LabMateEvidenceState;

typedef struct {
    LabMateEvidenceState state;
    uint32_t last_generation;
    bool sample_fault;
    LabMateCaptureEvidenceV1 evidence;
} LabMateEvidenceSession;

void labmate_evidence_session_init(LabMateEvidenceSession* session);

/* Call only after the native firmware lease/IRQ has CONFIRMED acquisition.
 * Refuses unsupported pins, zero clock, no lease, active sessions, and
 * generation wrap. One monotonically increasing generation per app epoch.
 */
bool labmate_evidence_session_begin(
    LabMateEvidenceSession* session, uint8_t source, uint8_t pin_index,
    uint32_t start_ms, uint32_t timebase_hz, bool ownership_confirmed);

/* App-thread submission of a completed coherent, verified measurement.
 * The cumulative completed-sample count AND observed-edge count must both
 * strictly increase on each report. The first complete sample requires at
 * least two observed edges. No edge-counter rollover is accepted in one
 * session; reset to a new independently owned capture epoch instead.
 * Rejected/out-of-order reports poison the session so the previous reading
 * cannot be replayed as VALID at STOP. Raw IRQ counts and sample counts
 * MUST be captured coherently by the real producer; this helper does not
 * infer them or provide the IRQ synchronization required to collect them.
 */
bool labmate_evidence_session_record(
    LabMateEvidenceSession* session, uint32_t completed_sample_count,
    uint32_t observed_edge_count, uint32_t dropped_edge_count,
    uint32_t frequency_millihz, uint32_t high_ticks, uint32_t low_ticks,
    uint32_t period_ticks, uint16_t duty_permille);

/* Call only AFTER the genuine IRQ and lease teardown attempt. The caller
 * supplies actual release result. Failed release is sticky: further START
 * cannot be represented as a safe session. Produces BUSY rather than VALID.
 * Bad/ambiguous elapsed time is reported CLOCK ERR without fake samples.
 */
bool labmate_evidence_session_finish(
    LabMateEvidenceSession* session, uint32_t end_ms,
    bool ownership_released, LabMateSnapshotV1* output);
