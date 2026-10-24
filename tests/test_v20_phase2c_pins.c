#include "labmate_snapshot_bridge.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static LabMateCaptureEvidenceV1 pulse(uint8_t index) {
    LabMateCaptureEvidenceV1 e={0};
    e.source=LabMateSnapshotPulse;
    e.pin_index=index;
    e.capture_generation=1;
    e.observation_start_ms=100;
    e.observation_end_ms=200;
    e.timebase_hz=64000000U;
    e.completed_sample_count=2;
    e.observed_edge_count=4;
    e.high_ticks=32000;
    e.low_ticks=32000;
    e.period_ticks=64000;
    e.duty_permille=500;
    e.measurement_valid=true;
    e.released=true;
    return e;
}
int main(void) {
    const uint8_t legal[]={0U,1U,3U,5U};
    const uint8_t illegal[]={2U,4U,6U,7U};
    for(unsigned i=0;i<4;i++) {
        const LabMateCaptureEvidenceV1 e=pulse(legal[i]);
        LabMateSnapshotV1 s={0};
        assert(labmate_snapshot_bridge_from_capture(&e,&s));
        assert(s.quality==LabMateSnapshotValid);
    }
    for(unsigned i=0;i<4;i++) {
        const LabMateCaptureEvidenceV1 e=pulse(illegal[i]);
        LabMateSnapshotV1 s={0};
        s.frequency_millihz=42;
        assert(!labmate_snapshot_bridge_from_capture(&e,&s));
        assert(s.frequency_millihz==42);
    }
    for(unsigned pin=0;pin<8;pin++) {
        LabMateCaptureEvidenceV1 e=pulse((uint8_t)pin);
        e.source=LabMateSnapshotFrequency;
        e.measured_frequency_millihz=100000U;
        LabMateSnapshotV1 s={0};
        const bool allowed=(pin==1U || pin==4U);
        assert(labmate_snapshot_capture_pin_supported(e.source,e.pin_index)==allowed);
        assert(labmate_snapshot_bridge_from_capture(&e,&s)==allowed);
        if(allowed)assert(s.quality==LabMateSnapshotValid);
    }
    for(unsigned pin=0;pin<8;pin++) {
        assert(labmate_snapshot_capture_pin_supported(LabMateSnapshotPulse,(uint8_t)pin)==
               (pin==0U || pin==1U || pin==3U || pin==5U));
    }
    assert(!labmate_snapshot_capture_pin_supported(LabMateSnapshotScope,1U));
    assert(!labmate_snapshot_capture_pin_supported(255U,1U));
    puts("UI-Phase2C strict E11 capture pin matrix PASS (8 Pulse, 8 Frequency, 2 unsupported sources)");
    return 0;
}
