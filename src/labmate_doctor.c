#include "labmate_doctor.h"

static uint32_t doctor_abs_delta_u32(uint32_t a, uint32_t b) {
    return a >= b ? a - b : b - a;
}

static bool doctor_valid_pulse_widths(const LabMateSnapshotV1* s) {
    if(s->high_ticks == 0U || s->low_ticks == 0U || s->period_ticks == 0U) return false;
    if((uint64_t)s->high_ticks + s->low_ticks != s->period_ticks) return false;
    /* Require the exact rounded permille rule of snapshot_bridge.c. */
    const uint64_t rounded = ((uint64_t)s->high_ticks * 1000U +
                              (uint64_t)s->period_ticks / 2U) / s->period_ticks;
    return rounded == s->duty_permille;
}

bool labmate_doctor_evaluate(
    const LabMateSnapshotV1* snapshot,
    const LabMateDoctorReference* reference,
    LabMateDoctorResult* result) {
    if(!snapshot || !reference || !result || reference->frequency_millihz == 0U ||
       reference->frequency_tolerance_permille > 1000U ||
       reference->expected_duty_permille > 1000U ||
       reference->duty_tolerance_permille > 1000U ||
       reference->minimum_no_signal_window_ms == 0U) return false;

    LabMateDoctorResult evaluated = {LabMateDoctorNotReady, false};
    if(!labmate_snapshot_v1_well_formed(snapshot)) {
        *result = evaluated;
        return true;
    }
    /* Phase 3A intentionally supports only capture-backed Frequency/Pulse.
     * Other sources need their own separately reviewed measurement contracts. */
    const bool freq_pin = snapshot->source == LabMateSnapshotFrequency &&
        (snapshot->pin_index == 1U || snapshot->pin_index == 4U);
    const bool pulse_pin = snapshot->source == LabMateSnapshotPulse &&
        (snapshot->pin_index == 0U || snapshot->pin_index == 1U ||
         snapshot->pin_index == 3U || snapshot->pin_index == 5U);
    /* Scope supplies only complete, released, nontruncated PC1 cycles.
     * Neither missing triggers nor still-owned IRQ buffers are accepted.
     */
    const bool scope_pin = snapshot->source == LabMateSnapshotScope &&
        snapshot->pin_index == 1U && snapshot->valid_sample_count >= 2U &&
        snapshot->observed_edge_count >= 5U;
    if(!freq_pin && !pulse_pin && !scope_pin) {
        *result = evaluated;
        return true;
    }
    if(snapshot->quality == LabMateSnapshotNoSignalConfirmed) {
        /* 'No signal observed' is an observation, not a device diagnosis.
         * Empty data, HOLD, BUSY and stale numeric values never pass here. */
        const uint32_t window_ms = snapshot->observation_end_ms -
                                   snapshot->observation_start_ms;
        if(snapshot->ownership_released && snapshot->timebase_hz > 0U &&
           window_ms >= reference->minimum_no_signal_window_ms &&
           snapshot->observed_edge_count == 0U &&
           snapshot->valid_sample_count == 0U &&
           snapshot->dropped_edge_count == 0U &&
           snapshot->frequency_millihz == 0U && snapshot->high_ticks == 0U &&
           snapshot->low_ticks == 0U && snapshot->period_ticks == 0U &&
           snapshot->duty_permille == 0U) {
            evaluated.verdict = LabMateDoctorNoSignalObserved;
            evaluated.evidence_accepted = true;
        }
        *result = evaluated;
        return true;
    }
    if(!labmate_snapshot_v1_can_display_measurement(snapshot) ||
       (snapshot->source == LabMateSnapshotPulse &&
        !doctor_valid_pulse_widths(snapshot))) {
        *result = evaluated;
        return true;
    }

    const uint64_t delta = doctor_abs_delta_u32(
        snapshot->frequency_millihz, reference->frequency_millihz);
    const bool freq_deviation = delta * 1000U >
        (uint64_t)reference->frequency_millihz * reference->frequency_tolerance_permille;
    const bool duty_deviation =
        (snapshot->source == LabMateSnapshotPulse ||
         snapshot->source == LabMateSnapshotScope) &&
        doctor_abs_delta_u32(snapshot->duty_permille,
                             reference->expected_duty_permille) >
            reference->duty_tolerance_permille;
    evaluated.evidence_accepted = true;
    evaluated.verdict = freq_deviation && duty_deviation ? LabMateDoctorMultipleDeviations :
                        freq_deviation ? LabMateDoctorFrequencyDeviation :
                        duty_deviation ? LabMateDoctorDutyDeviation :
                                         LabMateDoctorWithinExpected;
    *result = evaluated;
    return true;
}

const char* labmate_doctor_verdict_text(LabMateDoctorVerdict verdict) {
    switch(verdict) {
    case LabMateDoctorNotReady: return "NO DATA";
    case LabMateDoctorNoSignalObserved: return "NO SIG";
    case LabMateDoctorWithinExpected: return "IN RANGE";
    case LabMateDoctorFrequencyDeviation: return "FREQ DIFF";
    case LabMateDoctorDutyDeviation: return "DUTY DIFF";
    case LabMateDoctorMultipleDeviations: return "FREQ+DUTY";
    default: return "NO DATA";
    }
}
