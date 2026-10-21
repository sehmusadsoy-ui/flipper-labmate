#include "labmate_evidence_session.h"
#include <string.h>
#include <stdint.h>

void labmate_evidence_session_init(LabMateEvidenceSession* s) {
    if(s) memset(s, 0, sizeof(*s));
}

bool labmate_evidence_session_begin(
    LabMateEvidenceSession* s, uint8_t source, uint8_t pin_index,
    uint32_t start_ms, uint32_t timebase_hz, bool ownership_confirmed) {
    if(!s || !ownership_confirmed || timebase_hz == 0U ||
       (s->state != LabMateEvidenceIdle && s->state != LabMateEvidenceSealed) ||
       s->last_generation == UINT32_MAX ||
       !labmate_snapshot_capture_pin_supported(source, pin_index)) return false;
    ++s->last_generation;
    memset(&s->evidence, 0, sizeof(s->evidence));
    s->evidence.source = source;
    s->evidence.pin_index = pin_index;
    s->evidence.capture_generation = s->last_generation;
    s->evidence.observation_start_ms = start_ms;
    s->evidence.observation_end_ms = start_ms;
    s->evidence.timebase_hz = timebase_hz;
    s->sample_fault = false;
    s->state = LabMateEvidenceCapturing;
    return true;
}

bool labmate_evidence_session_record(
    LabMateEvidenceSession* s, uint32_t sample_count,
    uint32_t edge_count, uint32_t dropped_edge_count,
    uint32_t mhz, uint32_t high, uint32_t low,
    uint32_t period, uint16_t duty) {
    if(!s || s->state != LabMateEvidenceCapturing || s->sample_fault) return false;
    LabMateCaptureEvidenceV1* e = &s->evidence;
    if(sample_count == 0U || sample_count <= e->completed_sample_count ||
       edge_count < e->observed_edge_count ||
       dropped_edge_count < e->dropped_edge_count || duty > 1000U) {
        s->sample_fault = true;
        return false;
    }
    e->completed_sample_count = sample_count;
    e->observed_edge_count = edge_count;
    e->dropped_edge_count = dropped_edge_count;
    e->measured_frequency_millihz = mhz;
    e->high_ticks = high;
    e->low_ticks = low;
    e->period_ticks = period;
    e->duty_permille = duty;
    e->measurement_valid = true;
    return true;
}

bool labmate_evidence_session_finish(
    LabMateEvidenceSession* s, uint32_t end_ms,
    bool released, LabMateSnapshotV1* output) {
    if(!s || !output || s->state != LabMateEvidenceCapturing) return false;
    LabMateCaptureEvidenceV1 e = s->evidence;
    e.released = released;
    e.resource_busy = !released;
    if(end_ms <= e.observation_start_ms) {
        /* Same-epoch ordering cannot be proved. Keep a non-VALID status and
         * zero evidence: never fabricate a later timestamp to pass checks. */
        e.observation_end_ms = e.observation_start_ms;
        e.completed_sample_count = 0U;
        e.observed_edge_count = 0U;
        e.clock_unsafe = true;
    } else {
        e.observation_end_ms = end_ms;
    }
    if(s->sample_fault) e.measurement_valid = false;
    LabMateSnapshotV1 result;
    if(!labmate_snapshot_bridge_from_capture(&e, &result)) return false;
    /* A rejected/mismatched sample is not just missing: tag its lineage. */
    if(s->sample_fault && released && !e.clock_unsafe)
        result.quality = LabMateSnapshotInvalid;
    *output = result;
    s->evidence = e;
    s->state = released ? LabMateEvidenceSealed : LabMateEvidenceReleaseFault;
    return true;
}
