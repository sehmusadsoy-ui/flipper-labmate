#include "labmate_dashboard_store.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>

static LabMateSnapshotV1 good(uint8_t source, uint32_t generation) {
    LabMateSnapshotV1 s={0};
    s.schema_version=LABMATE_SNAPSHOT_VERSION;
    s.source=source;
    s.pin_index=1;
    s.quality=LabMateSnapshotValid;
    s.capture_generation=generation;
    s.observation_start_ms=5;
    s.observation_end_ms=500;
    s.timebase_hz=64000000U;
    s.valid_sample_count=4;
    s.observed_edge_count=8;
    s.frequency_millihz=1000000U;
    s.period_ticks=64000;
    s.duty_permille=500;
    s.ownership_released=true;
    return s;
}

int main(void) {
    unsigned cases=0;
    LabMateDashboardStore d;
    LabMateSnapshotV1 s, read={0};
    assert(sizeof(LabMateDashboardStore)<=512U);
    labmate_dashboard_store_init(&d);
    for(uint8_t source=0;source<LabMateSnapshotSourceCount;source++){
        assert(labmate_dashboard_store_quality(&d,source)==LabMateSnapshotInsufficient);
        assert(!labmate_dashboard_store_read_measurement(&d,source,&read));cases++;
    }
    assert(!labmate_dashboard_store_ingest(NULL,NULL));cases++;
    assert(!labmate_dashboard_store_read_measurement(NULL,0,&read));cases++;
    assert(!labmate_dashboard_store_read_measurement(&d,0,NULL));cases++;
    assert(labmate_dashboard_store_quality(&d,255)==LabMateSnapshotInsufficient);cases++;
    s=good(LabMateSnapshotFrequency,1);
    assert(labmate_dashboard_store_ingest(&d,&s));
    assert(labmate_dashboard_store_read_measurement(&d,s.source,&read));
    assert(read.capture_generation==1 && read.frequency_millihz==1000000);cases++;
    s.frequency_millihz=4000000; /* no silent replay of generation */
    assert(!labmate_dashboard_store_ingest(&d,&s));
    assert(labmate_dashboard_store_read_measurement(&d,s.source,&read));
    assert(read.frequency_millihz==1000000);cases++;
    s.capture_generation=2;s.quality=LabMateSnapshotBusy;
    assert(labmate_dashboard_store_ingest(&d,&s));
    assert(labmate_dashboard_store_quality(&d,s.source)==LabMateSnapshotBusy);
    read.frequency_millihz=123456U;
    assert(!labmate_dashboard_store_read_measurement(&d,s.source,&read));
    assert(read.frequency_millihz==123456U);cases++;
    s=good(LabMateSnapshotFrequency,3);s.ownership_released=false;
    assert(labmate_dashboard_store_ingest(&d,&s));
    assert(labmate_dashboard_store_quality(&d,s.source)==LabMateSnapshotInvalid);
    assert(!labmate_dashboard_store_read_measurement(&d,s.source,&read));cases++;
    s=good(LabMateSnapshotFrequency,4);
    assert(labmate_dashboard_store_ingest(&d,&s));
    assert(labmate_dashboard_store_read_measurement(&d,s.source,&read));cases++;
    s=good(LabMateSnapshotPulse,1);assert(labmate_dashboard_store_ingest(&d,&s));
    assert(labmate_dashboard_store_read_measurement(&d,s.source,&read));cases++;
    s=good(LabMateSnapshotScope,1);s.observed_edge_count=0;
    assert(labmate_dashboard_store_ingest(&d,&s));
    assert(labmate_dashboard_store_quality(&d,s.source)==LabMateSnapshotInvalid);
    assert(!labmate_dashboard_store_read_measurement(&d,s.source,&read));cases++;
    s=good(LabMateSnapshotCounter,1);s.observed_edge_count=0;s.frequency_millihz=0;
    assert(labmate_dashboard_store_ingest(&d,&s));
    assert(labmate_dashboard_store_read_measurement(&d,s.source,&read));cases++;
    s=good(LabMateSnapshotLogger,1);assert(labmate_dashboard_store_ingest(&d,&s));
    assert(labmate_dashboard_store_read_measurement(&d,s.source,&read));cases++;
    s=good(LabMateSnapshotFrequency,5);s.quality=LabMateSnapshotNoSignalConfirmed;
    s.observed_edge_count=0;
    assert(labmate_dashboard_store_ingest(&d,&s));
    assert(labmate_dashboard_store_quality(&d,s.source)==LabMateSnapshotNoSignalConfirmed);
    assert(!labmate_dashboard_store_read_measurement(&d,s.source,&read));cases++;
    s=good(LabMateSnapshotFrequency,6);s.quality=LabMateSnapshotStale;
    assert(labmate_dashboard_store_ingest(&d,&s));
    assert(!labmate_dashboard_store_read_measurement(&d,s.source,&read));cases++;
    s=good(LabMateSnapshotFrequency,7);s.quality=255;
    assert(!labmate_dashboard_store_ingest(&d,&s));
    assert(labmate_dashboard_store_quality(&d,s.source)==LabMateSnapshotStale);cases++;
    s=good(LabMateSnapshotFrequency,7);s.schema_version=2;
    assert(!labmate_dashboard_store_ingest(&d,&s));cases++;
    for(uint8_t source=0;source<LabMateSnapshotSourceCount;source++) {
        for(uint32_t generation=10;generation<=50;generation++) {
            s=good(source,generation);
            s.frequency_millihz=1000000+generation;
            assert(labmate_dashboard_store_ingest(&d,&s));
            assert(labmate_dashboard_store_read_measurement(&d,source,&read));
            assert(read.frequency_millihz==s.frequency_millihz);cases++;
            assert(!labmate_dashboard_store_ingest(&d,&s));cases++;
            s.capture_generation=generation-1;
            assert(!labmate_dashboard_store_ingest(&d,&s));cases++;
        }
    }
    puts("v2.0 dashboard read-only store PASS: fixed 5 sources, monotonic generations, no invalid numerical reads");
    printf("Dashboard host scenarios: %u\n",cases);
    return cases==637?0:1;
}
