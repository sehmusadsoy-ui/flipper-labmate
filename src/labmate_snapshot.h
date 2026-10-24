#pragma once
/* LabMate Ultimate v2.0: passive, versioned evidence format.
 * Pure C11. Not wired to capture or on-device storage in this phase.
 * Pin indices follow the legacy GPIO order, never renumber tool IDs.
 */
#include <stdbool.h>
#include <stdint.h>

#define LABMATE_SNAPSHOT_VERSION 1U
#define LABMATE_SNAPSHOT_PIN_COUNT 8U

typedef enum {
    LabMateSnapshotFrequency = 0,
    LabMateSnapshotPulse,
    LabMateSnapshotScope,
    LabMateSnapshotCounter,
    LabMateSnapshotLogger,
    LabMateSnapshotSourceCount
} LabMateSnapshotSource;

typedef enum {
    LabMateSnapshotValid = 0,
    LabMateSnapshotInsufficient,
    LabMateSnapshotNoSignalConfirmed,
    LabMateSnapshotBusy,
    LabMateSnapshotOverflow,
    LabMateSnapshotClockUnsafe,
    LabMateSnapshotInvalid,
    LabMateSnapshotStale,
    LabMateSnapshotQualityCount
} LabMateSnapshotQuality;

typedef struct {
    uint16_t schema_version;
    uint8_t source;
    uint8_t pin_index;
    uint8_t quality;
    bool ownership_released;
    uint32_t capture_generation;
    /* Device-monotonic milliseconds from the SAME acquisition epoch.
     * A wrapped or incompatible time window must not be treated as valid. */
    uint32_t observation_start_ms;
    uint32_t observation_end_ms;
    uint32_t timebase_hz;
    uint32_t valid_sample_count;
    uint32_t observed_edge_count;
    uint32_t dropped_edge_count;
    uint32_t frequency_millihz;
    uint16_t duty_permille;
    uint32_t high_ticks;
    uint32_t low_ticks;
    uint32_t period_ticks;
} LabMateSnapshotV1;

/* Structure sanity is NOT evidence that a capture happened. Producers must
 * explicitly assign quality based on real hardware observations. */
bool labmate_snapshot_v1_well_formed(const LabMateSnapshotV1* snapshot);

/* Dashboard eligibility: complete observation with genuine sample evidence,
 * safe same-epoch clock, no dropped edges, and released resource ownership.
 * No live capture or hardware access occurs here. */
bool labmate_snapshot_v1_can_display_measurement(const LabMateSnapshotV1* snapshot);

/* Safe text for an availability badge; never promotes an unknown quality. */
const char* labmate_snapshot_v1_quality_text(uint8_t quality);
