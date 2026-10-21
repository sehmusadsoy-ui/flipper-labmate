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
    puts("UI-Phase2C strict E11 Pulse pin allowlist PASS (4 allowed, 4 refused)");
    return 0;
}
