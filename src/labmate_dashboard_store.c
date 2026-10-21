#include "labmate_dashboard_store.h"
#include <string.h>

void labmate_dashboard_store_init(LabMateDashboardStore* store) {
    if(store) memset(store, 0, sizeof(*store));
}

bool labmate_dashboard_store_ingest(
    LabMateDashboardStore* store, const LabMateSnapshotV1* observation) {
    if(!store || !labmate_snapshot_v1_well_formed(observation)) return false;
    LabMateDashboardSlot* slot = &store->slots[observation->source];
    if(slot->has_snapshot &&
       observation->capture_generation <= slot->latest.capture_generation) return false;
    /* Do not permit an unsound VALID claim to leak as a displayed reading. */
    slot->latest = *observation;
    if(observation->quality == LabMateSnapshotValid &&
       !labmate_snapshot_v1_can_display_measurement(observation)) {
        slot->latest.quality = LabMateSnapshotInvalid;
    }
    slot->has_snapshot = true;
    return true;
}

LabMateSnapshotQuality labmate_dashboard_store_quality(
    const LabMateDashboardStore* store, uint8_t source) {
    if(!store || source >= LabMateSnapshotSourceCount ||
       !store->slots[source].has_snapshot) return LabMateSnapshotInsufficient;
    return (LabMateSnapshotQuality)store->slots[source].latest.quality;
}

bool labmate_dashboard_store_read_measurement(
    const LabMateDashboardStore* store, uint8_t source, LabMateSnapshotV1* output) {
    if(!store || !output || source >= LabMateSnapshotSourceCount ||
       !store->slots[source].has_snapshot) return false;
    const LabMateSnapshotV1* snapshot = &store->slots[source].latest;
    if(!labmate_snapshot_v1_can_display_measurement(snapshot)) return false;
    *output = *snapshot;
    return true;
}
