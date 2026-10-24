#pragma once
/* Phase 3A: passive, advisory signal classification from a SEALED snapshot.
 * Pure C11, no heap, IRQ, HAL, GPIO, clock sampling or filesystem access.
 * Never equate a diagnostic indication with hardware failure proof.
 */
#include "labmate_snapshot.h"

typedef enum {
    LabMateDoctorNotReady = 0,
    LabMateDoctorNoSignalObserved,
    LabMateDoctorWithinExpected,
    LabMateDoctorFrequencyDeviation,
    LabMateDoctorDutyDeviation,
    LabMateDoctorMultipleDeviations,
} LabMateDoctorVerdict;

typedef struct {
    /* Reference and tolerances supplied by user/profile, never inferred. */
    uint32_t frequency_millihz; /* Must be > 0. */
    uint16_t frequency_tolerance_permille; /* 0..1000 (relative to reference). */
    uint16_t expected_duty_permille; /* 0..1000; used for Pulse only. */
    uint16_t duty_tolerance_permille; /* Absolute duty difference, 0..1000. */
    uint32_t minimum_no_signal_window_ms; /* > 0; explicit observation period. */
} LabMateDoctorReference;

typedef struct {
    LabMateDoctorVerdict verdict;
    /* Only true for an eligible sealed measurement or explicitly confirmed
     * no-signal observation. Never infer from empty/stale/busy dashboards. */
    bool evidence_accepted;
} LabMateDoctorResult;

/* Returns false only for null pointers or invalid reference configuration;
 * does not modify result in that case. Otherwise emits NotReady unless the
 * measured evidence passes all conservative gates. Does not acquire data. */
bool labmate_doctor_evaluate(
    const LabMateSnapshotV1* snapshot,
    const LabMateDoctorReference* reference,
    LabMateDoctorResult* result);

const char* labmate_doctor_verdict_text(LabMateDoctorVerdict verdict);
