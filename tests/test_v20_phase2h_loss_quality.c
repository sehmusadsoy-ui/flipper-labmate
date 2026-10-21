#include "labmate_low_mailbox_evidence.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static LabMateCaptureEvidenceV1 genuine(void) {
    LabMateCaptureEvidenceV1 e = {0};
    e.source=LabMateSnapshotFrequency;
    e.pin_index=1;
    e.capture_generation=3;
    e.observation_start_ms=100;
    e.observation_end_ms=300;
    e.timebase_hz=64000000U;
    e.completed_sample_count=2;
    e.observed_edge_count=4;
    e.measured_frequency_millihz=100000U;
    e.period_ticks=640000U;
    e.measurement_valid=true;
    e.released=true;
    return e;
}
static LabMateSnapshotQuality quality(LabMateCaptureEvidenceV1* e) {
    LabMateSnapshotV1 s={0};
    assert(labmate_snapshot_bridge_from_capture(e,&s));
    return (LabMateSnapshotQuality)s.quality;
}
int main(void) {
    unsigned cases=0;
    LabMateCaptureEvidenceV1 e=genuine();
    LabMateLowMailboxObservation frame={.has_period=true,.period_cycles=640000U,.publications=1};
    assert(labmate_low_mailbox_apply_evidence(&frame,&e));
    assert(quality(&e)==LabMateSnapshotValid);cases++;
    e=genuine();frame.overwrites=1;
    assert(labmate_low_mailbox_apply_evidence(&frame,&e));
    assert(e.overflow && e.dropped_edge_count==0U);
    assert(quality(&e)==LabMateSnapshotOverflow);cases++;
    e=genuine();frame.overwrites=0;frame.exhausted=true;
    assert(labmate_low_mailbox_apply_evidence(&frame,&e));
    assert(quality(&e)==LabMateSnapshotOverflow);cases++;
    e=genuine();frame.exhausted=false;frame.publications=0;
    assert(labmate_low_mailbox_apply_evidence(&frame,&e));
    assert(!e.measurement_valid && quality(&e)==LabMateSnapshotInsufficient);cases++;
    e=genuine();frame.publications=1;frame.has_period=false;
    assert(labmate_low_mailbox_apply_evidence(&frame,&e));
    assert(!e.measurement_valid && quality(&e)==LabMateSnapshotInsufficient);cases++;
    e=genuine();frame.overwrites=2;
    assert(labmate_low_mailbox_apply_evidence(&frame,&e));
    assert(quality(&e)==LabMateSnapshotOverflow);cases++;
    e=genuine();frame.has_period=true;frame.overwrites=0;
    assert(!labmate_low_mailbox_apply_evidence(NULL,&e));cases++;
    assert(!labmate_low_mailbox_apply_evidence(&frame,NULL));cases++;
    e=genuine();e.source=LabMateSnapshotPulse;
    const LabMateCaptureEvidenceV1 old=e;
    assert(!labmate_low_mailbox_apply_evidence(&frame,&e));
    assert(!memcmp(&e,&old,sizeof(e)));cases++;
    e=genuine();e.pin_index=4;
    assert(!labmate_low_mailbox_apply_evidence(&frame,&e));cases++;
    e=genuine();e.resource_busy=true;frame.overwrites=9;
    assert(labmate_low_mailbox_apply_evidence(&frame,&e));
    assert(quality(&e)==LabMateSnapshotBusy);cases++;
    e=genuine();e.clock_unsafe=true;
    assert(labmate_low_mailbox_apply_evidence(&frame,&e));
    assert(quality(&e)==LabMateSnapshotClockUnsafe);cases++;
    // Host probe matrix: no detected overwrites -> baseline, any overwrite -> OVERFLOW.
    for(uint32_t k=0;k<1024U;++k) {
        e=genuine();
        frame=(LabMateLowMailboxObservation){.has_period=true,.period_cycles=640000U,.publications=k+1U,.overwrites=k};
        assert(labmate_low_mailbox_apply_evidence(&frame,&e));
        assert(quality(&e)==(k?LabMateSnapshotOverflow:LabMateSnapshotValid));
        assert(e.dropped_edge_count==0U);cases++;
    }
    printf("Phase2H PC1 overwrite -> Snapshot OVERFLOW PASS: %u quality cases\n",cases);
    return cases==1036U?0:1;
}
