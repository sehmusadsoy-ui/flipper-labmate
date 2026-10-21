#pragma once
/* Phase 2: fixed-capacity read-only dashboard projection of evidence.
 * Pure C, no heap, no Flipper HAL, GPIO or microSD access.
 */
#include "labmate_snapshot.h"

typedef struct {
    bool has_snapshot;
    LabMateSnapshotV1 latest;
} LabMateDashboardSlot;

typedef struct {
    LabMateDashboardSlot slots[LabMateSnapshotSourceCount];
} LabMateDashboardStore;

void labmate_dashboard_store_init(LabMateDashboardStore* store);

/* Observations are monotonically versioned per source. Out-of-order or
 * malformed events never overwrite a newer snapshot. A new BUSY/INVALID/etc
 * state immediately makes the previous validated reading unavailable.
 * A claimed VALID snapshot without sufficient evidence becomes INVALID.
 */
bool labmate_dashboard_store_ingest(
    LabMateDashboardStore* store, const LabMateSnapshotV1* observation);

/* Returns explicit status; empty slots are NO DATA, not STALE or LIVE. */
LabMateSnapshotQuality labmate_dashboard_store_quality(
    const LabMateDashboardStore* store, uint8_t source);

/* A caller cannot retrieve numeric values for BUSY, STALE, NO SIGNAL,
 * INVALID, OVERFLOW or any other non-VALID state. No pointer to internal
 * storage is returned, avoiding accidental mutation of dashboard evidence.
 */
bool labmate_dashboard_store_read_measurement(
    const LabMateDashboardStore* store, uint8_t source, LabMateSnapshotV1* output);
