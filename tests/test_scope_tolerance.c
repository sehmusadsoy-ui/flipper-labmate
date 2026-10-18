/* v1.9 pure-C measured-reference tolerance regression.
 * cc -std=c11 -Wall -Wextra -Werror -pedantic -Isrc \
 *   tests/test_scope_tolerance.c src/labmate_scope_tolerance.c \
 *   src/labmate_scope_compare.c -o /tmp/test_scope_tolerance
 * /tmp/test_scope_tolerance
 */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "labmate_scope_tolerance.h"

static LabMateScopeMetrics measured_1khz(void) {
    const LabMateScopeEdge captured[] = {
        {.tick = 100U, .delta_ticks = 0U, .high = true},
        {.tick = 600U, .delta_ticks = 500U, .high = false},
        {.tick = 1100U, .delta_ticks = 500U, .high = true},
    };
    LabMateScopeMetrics m =
        labmate_scope_metrics_from_edges(captured, 3U, 1000000U);
    assert(m.status == LabMateScopeMetricsReady);
    assert(m.frequency_millihz == UINT64_C(1000000));
    assert(m.duty_permille == 500U && m.completed_cycles == 1U);
    return m;
}

static void test_presets_and_limits(void) {
    LabMateScopeReference reference = {0};
    assert(!labmate_scope_reference_preset(
        LabMateScopeReference1kHz50, NULL));
    assert(labmate_scope_reference_preset(
        LabMateScopeReference100Hz50, &reference));
    assert(!strcmp(reference.name, "100Hz 50%"));
    assert(reference.expected_frequency_millihz == 100000U);
    assert(labmate_scope_reference_preset(
        LabMateScopeReference1kHz50, &reference));
    assert(!strcmp(reference.name, "1kHz 50%"));
    assert(reference.expected_frequency_millihz == 1000000U);
    const LabMateScopeReference copy = reference;
    assert(!labmate_scope_reference_preset(
        (LabMateScopeReferencePreset)99, &reference));
    assert(!memcmp(&reference, &copy, sizeof(reference)));

    LabMateScopeMetrics measured = measured_1khz();
    LabMateScopeToleranceResult r = labmate_scope_tolerance_evaluate(
        &reference, &measured, LabMateScopeObservationComplete);
    assert(r.verdict == LabMateScopeVerdictPass);
    assert(r.frequency_error_millihz == 0U && r.duty_error_permille == 0U);

    /* Exact tolerance limits are inclusive. */
    measured.frequency_millihz += 10000U;
    measured.duty_permille += 20U;
    r = labmate_scope_tolerance_evaluate(
        &reference, &measured, LabMateScopeObservationComplete);
    assert(r.verdict == LabMateScopeVerdictPass);
    assert(r.frequency_error_millihz == 10000U && r.duty_error_permille == 20U);
    ++measured.frequency_millihz;
    assert(labmate_scope_tolerance_evaluate(
        &reference, &measured, LabMateScopeObservationComplete).verdict ==
        LabMateScopeVerdictOutOfTolerance);
    measured = measured_1khz();
    measured.duty_permille = 479U;
    assert(labmate_scope_tolerance_evaluate(
        &reference, &measured, LabMateScopeObservationComplete).verdict ==
        LabMateScopeVerdictOutOfTolerance);
}

static void test_denials(void) {
    LabMateScopeReference reference = {0};
    assert(labmate_scope_reference_preset(
        LabMateScopeReference1kHz50, &reference));
    LabMateScopeMetrics m = measured_1khz();

    m.truncated = true; /* dropped edges or a filled capture */
    assert(labmate_scope_tolerance_evaluate(
        &reference, &m, LabMateScopeObservationComplete).verdict ==
        LabMateScopeVerdictInvalid);
    m = measured_1khz();
    m.timebase_hz = 0U;
    assert(labmate_scope_tolerance_evaluate(
        &reference, &m, LabMateScopeObservationComplete).verdict ==
        LabMateScopeVerdictInvalid);
    m = measured_1khz();
    m.completed_cycles = 0U;
    assert(labmate_scope_tolerance_evaluate(
        &reference, &m, LabMateScopeObservationComplete).verdict ==
        LabMateScopeVerdictInvalid);

    m = measured_1khz();
    assert(labmate_scope_tolerance_evaluate(
        &reference, &m, LabMateScopeObservationBusy).verdict ==
        LabMateScopeVerdictBusy);
    assert(labmate_scope_tolerance_evaluate(
        &reference, &m, LabMateScopeObservationInvalid).verdict ==
        LabMateScopeVerdictInvalid);
    assert(labmate_scope_tolerance_evaluate(
        &reference, &m, LabMateScopeObservationNoSignalConfirmed).verdict ==
        LabMateScopeVerdictInvalid); /* contradictory nonzero edges */

    m = (LabMateScopeMetrics){0};
    assert(labmate_scope_tolerance_evaluate(
        &reference, &m, LabMateScopeObservationNoSignalConfirmed).verdict ==
        LabMateScopeVerdictNoSignal);
    assert(labmate_scope_tolerance_evaluate(
        &reference, &m, LabMateScopeObservationComplete).verdict ==
        LabMateScopeVerdictInvalid); /* 0 edges is NOT NO_SIGNAL without timeout */

    reference.name[0] = '\0';
    assert(labmate_scope_tolerance_evaluate(
        &reference, &m, LabMateScopeObservationNoSignalConfirmed).verdict ==
        LabMateScopeVerdictInvalid);
    assert(labmate_scope_tolerance_evaluate(
        NULL, &m, LabMateScopeObservationNoSignalConfirmed).verdict ==
        LabMateScopeVerdictInvalid);
}

int main(void) {
    test_presets_and_limits();
    test_denials();
    puts("scope named reference / tolerance host regressions: PASS");
    return 0;
}
