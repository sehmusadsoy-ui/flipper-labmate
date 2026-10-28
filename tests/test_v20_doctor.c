#include "labmate_doctor.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static LabMateSnapshotV1 make_valid(uint8_t source) {
    LabMateSnapshotV1 s = {0};
    s.schema_version = LABMATE_SNAPSHOT_VERSION;
    s.source = source;
    s.pin_index = 1U; /* PC1 */
    s.quality = LabMateSnapshotValid;
    s.ownership_released = true;
    s.capture_generation = 1U;
    s.observation_start_ms = 100U;
    s.observation_end_ms = 1100U;
    s.timebase_hz = 64000000U;
    s.valid_sample_count = 10U;
    s.observed_edge_count = 22U;
    s.frequency_millihz = 1000000U;
    if(source == LabMateSnapshotPulse) {
        s.high_ticks = 32000U;
        s.low_ticks = 32000U;
        s.period_ticks = 64000U;
        s.duty_permille = 500U;
    }
    return s;
}
static const LabMateDoctorReference ref = {1000000U, 10U, 500U, 20U, 200U};
static int scenarios;

static void expect_verdict(LabMateSnapshotV1 s, LabMateDoctorVerdict v, bool accepted) {
    LabMateDoctorResult out = {LabMateDoctorMultipleDeviations, true};
    assert(labmate_doctor_evaluate(&s, &ref, &out));
    assert(out.verdict == v && out.evidence_accepted == accepted);
    scenarios++;
}
int main(void) {
    LabMateSnapshotV1 s = make_valid(LabMateSnapshotFrequency);
    expect_verdict(s, LabMateDoctorWithinExpected, true);
    s.frequency_millihz = 1010000U; /* +1%, inclusive boundary */
    expect_verdict(s, LabMateDoctorWithinExpected, true);
    s.frequency_millihz = 1010001U;
    expect_verdict(s, LabMateDoctorFrequencyDeviation, true);
    s.frequency_millihz = 990000U;
    expect_verdict(s, LabMateDoctorWithinExpected, true);
    s.frequency_millihz = 989999U;
    expect_verdict(s, LabMateDoctorFrequencyDeviation, true);
    s = make_valid(LabMateSnapshotPulse);
    expect_verdict(s, LabMateDoctorWithinExpected, true);
    s.high_ticks = 33280U;
    s.low_ticks = 30720U;
    s.duty_permille = 520U;
    expect_verdict(s, LabMateDoctorWithinExpected, true); /* absolute boundary */
    s.high_ticks = 33344U; s.low_ticks = 30656U; s.duty_permille = 521U;
    expect_verdict(s, LabMateDoctorDutyDeviation, true);
    s.frequency_millihz = 1020000U;
    expect_verdict(s, LabMateDoctorMultipleDeviations, true);
    s.duty_permille = 500U; /* contradicts captured widths */
    expect_verdict(s, LabMateDoctorNotReady, false);
    s = make_valid(LabMateSnapshotPulse);
    s.high_ticks = 1001U; s.low_ticks = 999U;
    s.period_ticks = 2000U; s.duty_permille = 500U;
    expect_verdict(s, LabMateDoctorNotReady, false); /* round-up tie */
    s = make_valid(LabMateSnapshotPulse);
    s.high_ticks = UINT32_MAX;
    expect_verdict(s, LabMateDoctorNotReady, false); /* sum mismatch/overflow safe */
    s = make_valid(LabMateSnapshotFrequency);
    s.ownership_released = false;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s.ownership_released = true; s.dropped_edge_count = 1U;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s = make_valid(LabMateSnapshotFrequency); s.quality = LabMateSnapshotStale;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s.quality = LabMateSnapshotBusy;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s.quality = LabMateSnapshotOverflow;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s.quality = LabMateSnapshotClockUnsafe;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s.quality = LabMateSnapshotInsufficient;
    expect_verdict(s, LabMateDoctorNotReady, false);
    /* Current Doctor only assesses Frequency and Pulse. Scope has a
     * separate symptom analyzer and cannot be silently treated as Pulse. */
    s = make_valid(LabMateSnapshotScope);
    s.duty_permille = 500U;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s.duty_permille = 525U;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s.pin_index = 4U; /* Scope only has a verified PC1 capture owner */
    expect_verdict(s, LabMateDoctorNotReady, false);
    s = make_valid(LabMateSnapshotScope);
    s.duty_permille = 500U; s.valid_sample_count = 1U;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s = make_valid(LabMateSnapshotPulse); s.pin_index = 4U;
    expect_verdict(s, LabMateDoctorNotReady, false); /* Pulse cannot use PB3 */
    s = make_valid(LabMateSnapshotFrequency); s.pin_index = 0U;
    expect_verdict(s, LabMateDoctorNotReady, false); /* Frequency cannot use PC0 */
    s = make_valid(LabMateSnapshotFrequency); s.pin_index = 4U;
    expect_verdict(s, LabMateDoctorWithinExpected, true); /* PB3 HIGH accepted */
    s = make_valid(LabMateSnapshotPulse); s.pin_index = 3U;
    expect_verdict(s, LabMateDoctorWithinExpected, true); /* PB2 EXTI accepted */
    s = make_valid(LabMateSnapshotFrequency); s.schema_version = 2U;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s = make_valid(LabMateSnapshotFrequency); s.observation_start_ms = 2000U;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s = make_valid(LabMateSnapshotFrequency); s.valid_sample_count = 0U;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s = make_valid(LabMateSnapshotFrequency); s.observed_edge_count = 0U;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s = make_valid(LabMateSnapshotFrequency); s.frequency_millihz = UINT32_MAX;
    expect_verdict(s, LabMateDoctorFrequencyDeviation, true);
    s = make_valid(LabMateSnapshotFrequency);
    s.frequency_millihz = 1U;
    expect_verdict(s, LabMateDoctorFrequencyDeviation, true);

    s = make_valid(LabMateSnapshotFrequency);
    s.quality = LabMateSnapshotNoSignalConfirmed;
    s.frequency_millihz = 0U;
    s.valid_sample_count = 0U;
    s.observed_edge_count = 0U;
    expect_verdict(s, LabMateDoctorNoSignalObserved, true);
    s.observation_end_ms = 299U; /* just below 200ms window */
    expect_verdict(s, LabMateDoctorNotReady, false);
    s.observation_end_ms = 300U; /* exact threshold */
    expect_verdict(s, LabMateDoctorNoSignalObserved, true);
    s.observed_edge_count = 1U;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s.observed_edge_count = 0U;
    s.ownership_released = false;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s.ownership_released = true;
    s.dropped_edge_count = 1U;
    expect_verdict(s, LabMateDoctorNotReady, false);
    s.dropped_edge_count = 0U;
    s.frequency_millihz = 1000000U;
    expect_verdict(s, LabMateDoctorNotReady, false); /* refuse stale number */
    s.frequency_millihz = 0U;
    s.timebase_hz = 0U;
    expect_verdict(s, LabMateDoctorNotReady, false);

    LabMateDoctorResult out = {LabMateDoctorWithinExpected, true};
    LabMateDoctorReference bad = ref;
    assert(!labmate_doctor_evaluate(NULL, &ref, &out));
    assert(!labmate_doctor_evaluate(&s, NULL, &out));
    assert(!labmate_doctor_evaluate(&s, &ref, NULL));
    bad.frequency_millihz = 0U;
    assert(!labmate_doctor_evaluate(&s, &bad, &out));
    bad = ref; bad.frequency_tolerance_permille = 1001U;
    assert(!labmate_doctor_evaluate(&s, &bad, &out));
    bad = ref; bad.expected_duty_permille = 1001U;
    assert(!labmate_doctor_evaluate(&s, &bad, &out));
    bad = ref; bad.duty_tolerance_permille = 1001U;
    assert(!labmate_doctor_evaluate(&s, &bad, &out));
    bad = ref; bad.minimum_no_signal_window_ms = 0U;
    assert(!labmate_doctor_evaluate(&s, &bad, &out));
    assert(out.verdict == LabMateDoctorWithinExpected && out.evidence_accepted);
    assert(strcmp(labmate_doctor_verdict_text(LabMateDoctorNoSignalObserved), "NO SIG") == 0);
    assert(strcmp(labmate_doctor_verdict_text((LabMateDoctorVerdict)123), "NO DATA") == 0);
    printf("PHASE3A SIGNAL DOCTOR HOST PASS: %d evidence scenarios + 8 bad-input gates\n", scenarios);
    return 0;
}
