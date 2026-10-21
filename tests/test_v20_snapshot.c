#include "labmate_snapshot.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>

static LabMateSnapshotV1 measured(void) {
    LabMateSnapshotV1 s={0};
    s.schema_version=LABMATE_SNAPSHOT_VERSION;
    s.source=LabMateSnapshotFrequency;
    s.pin_index=1;
    s.quality=LabMateSnapshotValid;
    s.capture_generation=1;
    s.observation_start_ms=100;
    s.observation_end_ms=1100;
    s.timebase_hz=64000000U;
    s.valid_sample_count=3;
    s.observed_edge_count=6;
    s.frequency_millihz=1000000U;
    s.duty_permille=500;
    s.ownership_released=true;
    return s;
}

int main(void) {
    unsigned cases=0;
    LabMateSnapshotV1 s=measured();
    assert(labmate_snapshot_v1_well_formed(&s));
    assert(labmate_snapshot_v1_can_display_measurement(&s));cases++;
    assert(!labmate_snapshot_v1_well_formed(NULL));
    assert(!labmate_snapshot_v1_can_display_measurement(NULL));cases++;
#define REJECT_BAD(field,value) do { \
    s=measured();s.field=(value); \
    assert(!labmate_snapshot_v1_well_formed(&s)); \
    assert(!labmate_snapshot_v1_can_display_measurement(&s));cases++; \
} while(0)
    REJECT_BAD(schema_version,0);
    REJECT_BAD(schema_version,2);
    REJECT_BAD(source,LabMateSnapshotSourceCount);
    REJECT_BAD(pin_index,LABMATE_SNAPSHOT_PIN_COUNT);
    REJECT_BAD(quality,LabMateSnapshotQualityCount);
    REJECT_BAD(capture_generation,0);
    REJECT_BAD(duty_permille,1001);
    REJECT_BAD(observation_end_ms,99);
    REJECT_BAD(observation_end_ms,100);
#undef REJECT_BAD
#define REJECT_READING(field,value) do { \
    s=measured();s.field=(value); \
    assert(labmate_snapshot_v1_well_formed(&s)); \
    assert(!labmate_snapshot_v1_can_display_measurement(&s));cases++; \
} while(0)
    REJECT_READING(valid_sample_count,0);
    REJECT_READING(timebase_hz,0);
    REJECT_READING(dropped_edge_count,1);
    REJECT_READING(ownership_released,false);
    REJECT_READING(observed_edge_count,0);
    REJECT_READING(observed_edge_count,1);
    REJECT_READING(frequency_millihz,0);
#undef REJECT_READING
    s=measured();s.source=LabMateSnapshotPulse;
    s.period_ticks=64000;s.high_ticks=32000;s.low_ticks=32000;
    assert(labmate_snapshot_v1_can_display_measurement(&s));cases++;
    s.period_ticks=0;assert(!labmate_snapshot_v1_can_display_measurement(&s));cases++;
    s=measured();s.source=LabMateSnapshotCounter;s.observed_edge_count=0;
    s.frequency_millihz=0;
    assert(labmate_snapshot_v1_can_display_measurement(&s));cases++;
    s=measured();s.source=LabMateSnapshotScope;s.observed_edge_count=0;
    assert(!labmate_snapshot_v1_can_display_measurement(&s));cases++;
    s.observed_edge_count=1;
    assert(labmate_snapshot_v1_can_display_measurement(&s));cases++;
    s=measured();s.source=LabMateSnapshotLogger;s.observed_edge_count=0;
    assert(labmate_snapshot_v1_can_display_measurement(&s));cases++;
    for(uint8_t q=LabMateSnapshotInsufficient;q<LabMateSnapshotQualityCount;q++) {
        s=measured();s.quality=q;
        if(q==LabMateSnapshotNoSignalConfirmed)s.observed_edge_count=0;
        assert(labmate_snapshot_v1_well_formed(&s));
        assert(!labmate_snapshot_v1_can_display_measurement(&s));cases++;
    }
    s=measured();s.quality=LabMateSnapshotNoSignalConfirmed;s.observed_edge_count=3;
    assert(!labmate_snapshot_v1_well_formed(&s));cases++;
    s.observed_edge_count=0;s.observation_end_ms=s.observation_start_ms;
    assert(!labmate_snapshot_v1_well_formed(&s));cases++;
    for(unsigned q=0;q<256;q++) {
        const char* text=labmate_snapshot_v1_quality_text((uint8_t)q);
        assert(text && text[0] && strlen(text)<=9U);cases++;
        if(q>=LabMateSnapshotQualityCount)assert(!strcmp(text,"INVALID"));
    }
    s=measured();s.observation_end_ms=UINT32_MAX;
    assert(labmate_snapshot_v1_can_display_measurement(&s));cases++;
    printf("v2.0 snapshot host PASS: %u source/quality/invalid-input assertions\n",cases);
    return 0;
}
