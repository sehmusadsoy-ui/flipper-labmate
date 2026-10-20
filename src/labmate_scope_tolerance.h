#pragma once
/* v1.9 Signal Compare tolerance decision, pure C and host-testable.
 * This is a logic engine only; connecting preset controls to the real Flipper
 * UI and proving actual timing remain separate integration gates.
 */
#include <stdbool.h>
#include <stdint.h>
#include "labmate_scope_compare.h"

typedef enum {
    LabMateScopeReference100Hz50 = 0,
    LabMateScopeReference1kHz50,
} LabMateScopeReferencePreset;

typedef struct {
    char name[16]; /* copied, NUL terminated; no borrowed storage */
    uint64_t expected_frequency_millihz;
    uint16_t expected_duty_permille;
    uint64_t frequency_tolerance_millihz; /* absolute Hz * 1000 */
    uint16_t duty_tolerance_permille; /* absolute percentage points * 10 */
} LabMateScopeReference;

typedef enum {
    LabMateScopeObservationComplete = 0,
    LabMateScopeObservationNoSignalConfirmed,
    LabMateScopeObservationBusy,
    LabMateScopeObservationInvalid,
} LabMateScopeObservation;

typedef enum {
    LabMateScopeVerdictInvalid = 0,
    LabMateScopeVerdictPass,
    LabMateScopeVerdictOutOfTolerance,
    LabMateScopeVerdictNoSignal,
    LabMateScopeVerdictBusy,
} LabMateScopeVerdict;

typedef struct {
    LabMateScopeVerdict verdict;
    uint64_t frequency_error_millihz;
    uint16_t duty_error_permille;
} LabMateScopeToleranceResult;

/* Fixed examples, not an assertion that any real test was measured. */
bool labmate_scope_reference_preset(
    LabMateScopeReferencePreset preset, LabMateScopeReference* out);

/* Use only fully observed and valid measurements. No tolerance verdict is
 * computed for truncated, partial, clock-invalid or still-armed captures.
 * NO_SIGNAL requires independently confirmed capture timeout with zero
 * observed signal, not merely absent data at a display refresh.
 */
LabMateScopeToleranceResult labmate_scope_tolerance_evaluate(
    const LabMateScopeReference* reference,
    const LabMateScopeMetrics* measured,
    LabMateScopeObservation observation);
