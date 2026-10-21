#include "labmate_dashboard_store.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static LabMateSnapshotV1 sample(uint8_t source, uint32_t generation) {
    LabMateSnapshotV1 s={0};
    s.schema_version=LABMATE_SNAPSHOT_VERSION;
    s.source=source;s.pin_index=(source==LabMateSnapshotCounter)?4:1;
    s.quality=LabMateSnapshotValid;s.ownership_released=true;
    s.capture_generation=generation;
    s.observation_start_ms=100;s.observation_end_ms=200;
    s.timebase_hz=64000000;s.valid_sample_count=3;
    s.observed_edge_count=6;s.frequency_millihz=100000;
    if(source==LabMateSnapshotPulse) {
        s.high_ticks=320000;s.low_ticks=320000;s.period_ticks=640000;
        s.duty_permille=500;
    }
    return s;
}
int main(void){
    LabMateDashboardStore d;
    labmate_dashboard_store_init(&d);
    for(uint8_t i=0;i<LabMateSnapshotSourceCount;i++)
        assert(labmate_dashboard_store_quality(&d,i)==LabMateSnapshotInsufficient);
    for(uint8_t i=0;i<LabMateSnapshotSourceCount;i++) {
        LabMateSnapshotV1 s=sample(i,1);
        if(i==LabMateSnapshotCounter||i==LabMateSnapshotLogger)
            s.frequency_millihz=0;
        assert(labmate_dashboard_store_ingest(&d,&s));
    }
    for(uint8_t i=0;i<LabMateSnapshotSourceCount;i++){
        LabMateSnapshotV1 read={0};
        assert(labmate_dashboard_store_read_measurement(&d,i,&read));
        assert(read.source==i);
    }
    /* Invalidating Pulse may NEVER erase Counter or Scope. */
    labmate_dashboard_store_clear_source(&d,LabMateSnapshotPulse);
    assert(!d.slots[LabMateSnapshotPulse].has_snapshot);
    assert(d.slots[LabMateSnapshotScope].has_snapshot);
    assert(d.slots[LabMateSnapshotCounter].has_snapshot);
    assert(d.slots[LabMateSnapshotLogger].has_snapshot);
    /* Unsafe/busy cannot leak an earlier frequency into a displayed reading. */
    LabMateSnapshotV1 bad=sample(LabMateSnapshotFrequency,2);
    bad.quality=LabMateSnapshotBusy;
    assert(labmate_dashboard_store_ingest(&d,&bad));
    LabMateSnapshotV1 out={0};
    assert(!labmate_dashboard_store_read_measurement(&d,LabMateSnapshotFrequency,&out));
    assert(!labmate_dashboard_store_ingest(&d,&bad));
    bad.capture_generation=3;bad.quality=LabMateSnapshotValid;
    bad.ownership_released=false;
    assert(labmate_dashboard_store_ingest(&d,&bad));
    assert(!labmate_dashboard_store_read_measurement(&d,LabMateSnapshotFrequency,&out));
    assert(labmate_dashboard_store_quality(&d,LabMateSnapshotFrequency)==LabMateSnapshotInvalid);
    labmate_dashboard_store_clear_source(NULL,LabMateSnapshotPulse);
    labmate_dashboard_store_clear_source(&d,255U);
    puts("V20 DASHBOARD SEALED PROJECTION PASS: five sources, no replay, source-isolation, fail closed");
    return 0;
}
