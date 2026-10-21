#include "labmate_snapshot.h"

bool labmate_snapshot_v1_well_formed(const LabMateSnapshotV1* s) {
    if(!s || s->schema_version != LABMATE_SNAPSHOT_VERSION) return false;
    if(s->source >= LabMateSnapshotSourceCount ||
       s->pin_index >= LABMATE_SNAPSHOT_PIN_COUNT ||
       s->quality >= LabMateSnapshotQualityCount) return false;
    if(s->capture_generation == 0U || s->duty_permille > 1000U) return false;
    if(s->observation_end_ms < s->observation_start_ms) return false;
    if(s->valid_sample_count > 0U &&
       s->observation_end_ms == s->observation_start_ms) return false;
    if(s->quality == LabMateSnapshotNoSignalConfirmed) {
        /* A no-signal claim needs an explicit observed interval with no edges;
         * this validation alone does not establish sufficient duration. */
        if(s->observation_end_ms == s->observation_start_ms ||
           s->observed_edge_count != 0U) return false;
    }
    return true;
}

bool labmate_snapshot_v1_can_display_measurement(const LabMateSnapshotV1* s) {
    if(!labmate_snapshot_v1_well_formed(s) ||
       s->quality != LabMateSnapshotValid) return false;
    if(s->valid_sample_count == 0U || s->timebase_hz == 0U ||
       s->dropped_edge_count != 0U || !s->ownership_released) return false;
    /* Frequency and Pulse require observed transitions; a time window with
     * zero edges is not permission to invent a numeric measurement. */
    if((s->source == LabMateSnapshotFrequency ||
        s->source == LabMateSnapshotPulse) &&
       (s->observed_edge_count < 2U || s->frequency_millihz == 0U)) return false;
    if(s->source == LabMateSnapshotPulse && s->period_ticks == 0U) return false;
    if(s->source == LabMateSnapshotScope && s->observed_edge_count == 0U) return false;
    return true;
}

const char* labmate_snapshot_v1_quality_text(uint8_t quality) {
    switch(quality) {
    case LabMateSnapshotValid: return "VALID";
    case LabMateSnapshotInsufficient: return "NO DATA";
    case LabMateSnapshotNoSignalConfirmed: return "NO SIG";
    case LabMateSnapshotBusy: return "BUSY";
    case LabMateSnapshotOverflow: return "OVERFLOW";
    case LabMateSnapshotClockUnsafe: return "CLOCK ERR";
    case LabMateSnapshotInvalid: return "INVALID";
    case LabMateSnapshotStale: return "STALE";
    default: return "INVALID";
    }
}
