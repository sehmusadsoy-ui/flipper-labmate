#include "labmate_snapshot_bridge.h"
#include "labmate_dashboard_store.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>

static LabMateCaptureEvidenceV1 low(void) {
    LabMateCaptureEvidenceV1 e={0};
    e.source=LabMateSnapshotFrequency;
    e.pin_index=1;
    e.capture_generation=4;
    e.observation_start_ms=100;
    e.observation_end_ms=1000;
    e.timebase_hz=64000000U;
    e.completed_sample_count=4;
    e.observed_edge_count=8;
    e.measured_frequency_millihz=100000U;
    e.period_ticks=640000U;
    e.measurement_valid=true;
    e.released=true;
    return e;
}
static LabMateCaptureEvidenceV1 pulse(void) {
    LabMateCaptureEvidenceV1 e=low();
    e.source=LabMateSnapshotPulse;
    e.measured_frequency_millihz=0;
    e.high_ticks=32000;
    e.low_ticks=32000;
    e.period_ticks=64000;
    e.duty_permille=500;
    return e;
}
int main(void) {
    unsigned n=0;
    LabMateSnapshotV1 s={0};
    LabMateCaptureEvidenceV1 e=low();
    assert(labmate_snapshot_bridge_from_capture(&e,&s));
    assert(s.quality==LabMateSnapshotValid && s.frequency_millihz==100000U);
    assert(labmate_snapshot_v1_can_display_measurement(&s));n++;
    LabMateDashboardStore dashboard;
    labmate_dashboard_store_init(&dashboard);
    assert(labmate_dashboard_store_ingest(&dashboard,&s));n++;
    e=pulse();assert(labmate_snapshot_bridge_from_capture(&e,&s));
    assert(s.quality==LabMateSnapshotValid && s.frequency_millihz==1000000U && s.duty_permille==500);
    assert(labmate_dashboard_store_ingest(&dashboard,&s));n++;
    e=pulse();e.capture_generation=5;e.resource_busy=true;
    assert(labmate_snapshot_bridge_from_capture(&e,&s));
    assert(s.quality==LabMateSnapshotBusy);
    assert(labmate_dashboard_store_ingest(&dashboard,&s));
    assert(!labmate_dashboard_store_read_measurement(&dashboard,LabMateSnapshotPulse,&s));n++;
    e=pulse();e.released=false;e.capture_generation=6;
    assert(labmate_snapshot_bridge_from_capture(&e,&s));
    assert(s.quality==LabMateSnapshotBusy);n++;
    e=pulse();e.clock_unsafe=true;assert(labmate_snapshot_bridge_from_capture(&e,&s));
    assert(s.quality==LabMateSnapshotClockUnsafe);n++;
    e=pulse();e.timebase_hz=0;assert(labmate_snapshot_bridge_from_capture(&e,&s));
    assert(s.quality==LabMateSnapshotClockUnsafe);n++;
    e=pulse();e.dropped_edge_count=1;assert(labmate_snapshot_bridge_from_capture(&e,&s));
    assert(s.quality==LabMateSnapshotOverflow);n++;
    e=pulse();e.overflow=true;assert(labmate_snapshot_bridge_from_capture(&e,&s));
    assert(s.quality==LabMateSnapshotOverflow);n++;
    e=pulse();e.measurement_valid=false;assert(labmate_snapshot_bridge_from_capture(&e,&s));
    assert(s.quality==LabMateSnapshotInsufficient);n++;
    e=pulse();e.completed_sample_count=0;assert(labmate_snapshot_bridge_from_capture(&e,&s));
    assert(s.quality==LabMateSnapshotInsufficient);n++;
    e=pulse();e.observed_edge_count=0;assert(labmate_snapshot_bridge_from_capture(&e,&s));
    assert(s.quality==LabMateSnapshotInsufficient);n++;
    e=pulse();e.high_ticks=UINT32_MAX;e.low_ticks=1U;e.period_ticks=UINT32_MAX;
    assert(labmate_snapshot_bridge_from_capture(&e,&s) && s.quality==LabMateSnapshotInvalid);n++;
    e=pulse();e.high_ticks=32000;e.low_ticks=32001;
    assert(labmate_snapshot_bridge_from_capture(&e,&s) && s.quality==LabMateSnapshotInvalid);n++;
    e=pulse();e.duty_permille=499;
    assert(labmate_snapshot_bridge_from_capture(&e,&s) && s.quality==LabMateSnapshotInvalid);n++;
    e=pulse();e.period_ticks=0;
    assert(labmate_snapshot_bridge_from_capture(&e,&s) && s.quality==LabMateSnapshotInvalid);n++;
    e=pulse();e.period_ticks=64000;e.high_ticks=0;e.low_ticks=64000;e.duty_permille=0;
    assert(labmate_snapshot_bridge_from_capture(&e,&s) && s.quality==LabMateSnapshotValid);n++;
    e=pulse();e.period_ticks=64000;e.high_ticks=64000;e.low_ticks=0;e.duty_permille=1000;
    assert(labmate_snapshot_bridge_from_capture(&e,&s) && s.quality==LabMateSnapshotValid);n++;
    e=low();e.measured_frequency_millihz=0;
    assert(labmate_snapshot_bridge_from_capture(&e,&s) && s.quality==LabMateSnapshotInvalid);n++;
    e=low();e.pin_index=4;e.period_ticks=0; /* PB3 TIM2 requires no synthetic period */
    assert(labmate_snapshot_bridge_from_capture(&e,&s) && s.quality==LabMateSnapshotValid);n++;
    const LabMateSnapshotV1 prior=s;
#define REFUSE(change) do { \
    e=low();change; \
    assert(!labmate_snapshot_bridge_from_capture(&e,&s)); \
    assert(memcmp(&s,&prior,sizeof(s))==0);n++; \
} while(0)
    REFUSE(e.source=LabMateSnapshotScope);
    REFUSE(e.source=255);
    REFUSE(e.pin_index=8);
    REFUSE(e.pin_index=0); /* Frequency pins are PC1 or PB3 only. */
    REFUSE(e.capture_generation=0);
    REFUSE(e.observation_end_ms=99);
#undef REFUSE
    assert(!labmate_snapshot_bridge_from_capture(NULL,&s));n++;
    assert(!labmate_snapshot_bridge_from_capture(&e,NULL));n++;
    for(unsigned i=1;i<=255;i++) {
        e=low();e.capture_generation=i;
        e.measured_frequency_millihz=i*1000U;
        assert(labmate_snapshot_bridge_from_capture(&e,&s));
        assert(s.frequency_millihz==i*1000U);
        assert(s.capture_generation==i);
        n++;
    }
    printf("Phase2B snapshot bridge PASS: %u cases\n",n);
    return 0;
}
