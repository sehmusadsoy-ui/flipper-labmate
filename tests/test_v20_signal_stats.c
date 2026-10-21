#include "labmate_signal_stats.h"
#include <assert.h>
#include <stdio.h>
static LabMateSnapshotV1 valid(uint8_t source,uint32_t f) {
    LabMateSnapshotV1 s = {0};
    s.schema_version=LABMATE_SNAPSHOT_VERSION;
    s.source=source;s.pin_index=1;s.capture_generation=1;
    s.quality=LabMateSnapshotValid;s.ownership_released=true;
    s.observation_start_ms=100;s.observation_end_ms=200;
    s.timebase_hz=64000000;s.valid_sample_count=4;
    s.observed_edge_count=8;s.frequency_millihz=f;
    if(source==LabMateSnapshotPulse) {
       s.high_ticks=32000;s.low_ticks=32000;s.period_ticks=64000;
       s.duty_permille=500;
    }
    return s;
}
int main(void) {
    LabMateSignalStats st;
    labmate_signal_stats_init(&st);
    uint32_t mean=0,min=0,max=0;uint8_t n=0;
    assert(!labmate_signal_stats_read(&st,0,&mean,&min,&max,&n));
    LabMateSnapshotV1 s=valid(LabMateSnapshotFrequency,100000);
    assert(labmate_signal_stats_record(&st,&s));
    s.frequency_millihz=101000;
    assert(labmate_signal_stats_record(&st,&s));
    assert(labmate_signal_stats_read(&st,0,&mean,&min,&max,&n));
    assert(n==2&&mean==100500&&min==100000&&max==101000);
    s.quality=LabMateSnapshotBusy;
    assert(!labmate_signal_stats_record(&st,&s));
    s.quality=LabMateSnapshotValid;s.ownership_released=false;
    assert(!labmate_signal_stats_record(&st,&s));
    s.ownership_released=true;s.observed_edge_count=0;
    assert(!labmate_signal_stats_record(&st,&s));
    s=valid(LabMateSnapshotPulse,100000);
    assert(labmate_signal_stats_record(&st,&s));
    assert(labmate_signal_stats_read(&st,1,&mean,&min,&max,&n));
    assert(n==1&&mean==100000);
    s=valid(LabMateSnapshotScope,100000);
    assert(!labmate_signal_stats_record(&st,&s));
    s=valid(LabMateSnapshotFrequency,100000);
    for(unsigned i=2;i<LABMATE_SIGNAL_STATS_MAX_SESSIONS;i++)
        assert(labmate_signal_stats_record(&st,&s));
    assert(!labmate_signal_stats_record(&st,&s));
    assert(labmate_signal_stats_read(&st,0,&mean,&min,&max,&n));
    assert(n==LABMATE_SIGNAL_STATS_MAX_SESSIONS);
    puts("V20 SEALED SESSION STATS PASS: bound, mean, min/max, invalid/busy veto");
    return 0;
}
