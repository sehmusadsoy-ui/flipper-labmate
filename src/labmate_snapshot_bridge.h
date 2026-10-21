#pragma once
/* Phase 2B: app-thread, read-only handoff of ALREADY VERIFIED capture facts.
 * This API NEVER reads ISR fields or acquires/releases resources.
 * A producer must record generation/time window/sample counts at the original
 * acquisition; none may be inferred from a currently displayed HOLD value.
 */
#include "labmate_snapshot.h"

typedef struct {
    uint8_t source; /* Only Frequency and Pulse are supported at this gate. */
    uint8_t pin_index;
    uint32_t capture_generation;
    uint32_t observation_start_ms;
    uint32_t observation_end_ms;
    uint32_t timebase_hz;
    uint32_t completed_sample_count; /* Genuine completed periods; no guessed counts. */
    uint32_t observed_edge_count;
    uint32_t dropped_edge_count;
    uint32_t measured_frequency_millihz; /* Frequency producer only. */
    uint32_t high_ticks; /* Pulse producer only, from coherent app-thread copy. */
    uint32_t low_ticks;
    uint32_t period_ticks;
    uint16_t duty_permille; /* Pulse producer only. */
    bool measurement_valid; /* Trusted state from existing measurement calculation. */
    bool released; /* Explicit successful resource/IRQ teardown, NOT HOLD. */
    bool resource_busy;
    bool clock_unsafe;
    bool overflow;
} LabMateCaptureEvidenceV1;

/* Returns false for invalid input pointers/IDs/generation/timestamp order;
 * does not touch output on failure. For valid metadata writes an explicit
 * VALID / INSUFFICIENT / BUSY / CLOCK ERR / OVERFLOW / INVALID snapshot.
 * Every numerical reading is re-checked by labmate_snapshot_v1_can_display_measurement.
 * A no-signal diagnosis is NEVER inferred from missing samples here.
 */
bool labmate_snapshot_bridge_from_capture(
    const LabMateCaptureEvidenceV1* evidence, LabMateSnapshotV1* output);
