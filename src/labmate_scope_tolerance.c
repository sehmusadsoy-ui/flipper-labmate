#include "labmate_scope_tolerance.h"
#include <string.h>

bool labmate_scope_reference_preset(
    LabMateScopeReferencePreset preset, LabMateScopeReference* out) {
    if(!out) return false;
    LabMateScopeReference selected = {0};
    switch(preset) {
    case LabMateScopeReference100Hz50:
        memcpy(selected.name, "100Hz 50%", sizeof("100Hz 50%"));
        selected.expected_frequency_millihz = UINT64_C(100000);
        selected.frequency_tolerance_millihz = UINT64_C(1000);
        break;
    case LabMateScopeReference1kHz50:
        memcpy(selected.name, "1kHz 50%", sizeof("1kHz 50%"));
        selected.expected_frequency_millihz = UINT64_C(1000000);
        selected.frequency_tolerance_millihz = UINT64_C(10000);
        break;
    default:
        return false;
    }
    selected.expected_duty_permille = 500U;
    selected.duty_tolerance_permille = 20U;
    *out = selected;
    return true;
}

static bool labmate_scope_reference_valid(const LabMateScopeReference* r) {
    if(!r || r->name[0] == '\0' ||
       r->name[sizeof(r->name) - 1U] != '\0' ||
       !r->expected_frequency_millihz ||
       r->expected_duty_permille > 1000U ||
       r->duty_tolerance_permille > 1000U) return false;
    return true;
}

static bool labmate_scope_metric_valid(const LabMateScopeMetrics* m) {
    return m && m->status == LabMateScopeMetricsReady &&
           !m->truncated && m->completed_cycles > 0U &&
           m->edge_count >= 3U && m->edge_count <= LABMATE_SCOPE_MAX_EDGES &&
           m->timebase_hz > 0U && m->frequency_millihz > 0U &&
           m->frequency_millihz <= (uint64_t)m->timebase_hz * UINT64_C(500) &&
           m->duty_permille <= 1000U && m->min_period_ticks >= 2U &&
           m->max_period_ticks >= m->min_period_ticks;
}

LabMateScopeToleranceResult labmate_scope_tolerance_evaluate(
    const LabMateScopeReference* reference,
    const LabMateScopeMetrics* measured,
    LabMateScopeObservation observation) {
    LabMateScopeToleranceResult result = {.verdict = LabMateScopeVerdictInvalid};
    if(!labmate_scope_reference_valid(reference)) return result;

    if(observation == LabMateScopeObservationBusy) {
        result.verdict = LabMateScopeVerdictBusy;
        return result;
    }
    if(observation == LabMateScopeObservationNoSignalConfirmed) {
        /* Fail closed on contradictory supplied data. The caller must have
         * positively confirmed the no-trigger/no-edge timeout. */
        if(measured && measured->edge_count != 0U) return result;
        result.verdict = LabMateScopeVerdictNoSignal;
        return result;
    }
    if(observation != LabMateScopeObservationComplete ||
       !labmate_scope_metric_valid(measured)) return result;

    const uint64_t freq = measured->frequency_millihz;
    const uint64_t expected = reference->expected_frequency_millihz;
    result.frequency_error_millihz =
        freq >= expected ? freq - expected : expected - freq;
    const uint16_t duty = measured->duty_permille;
    const uint16_t desired = reference->expected_duty_permille;
    result.duty_error_permille = duty >= desired ? duty - desired : desired - duty;

    result.verdict =
        result.frequency_error_millihz <= reference->frequency_tolerance_millihz &&
        result.duty_error_permille <= reference->duty_tolerance_permille ?
            LabMateScopeVerdictPass : LabMateScopeVerdictOutOfTolerance;
    return result;
}
