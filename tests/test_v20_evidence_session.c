#include "labmate_evidence_session.h"
#include "labmate_dashboard_store.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    unsigned cases = 0;
    LabMateEvidenceSession s;
    LabMateSnapshotV1 out={0};
    labmate_evidence_session_init(&s);
    assert(s.state==LabMateEvidenceIdle && s.last_generation==0U);
    assert(!labmate_evidence_session_finish(&s,120,true,&out));cases++;
    assert(!labmate_evidence_session_begin(&s,LabMateSnapshotPulse,2,100,64000000U,true));cases++;
    assert(!labmate_evidence_session_begin(&s,LabMateSnapshotFrequency,1,100,0U,true));cases++;
    assert(!labmate_evidence_session_begin(&s,LabMateSnapshotFrequency,1,100,64000000U,false));cases++;
    assert(s.last_generation==0U);
    assert(labmate_evidence_session_begin(&s,LabMateSnapshotFrequency,1,100,64000000U,true));cases++;
    assert(s.last_generation==1U && s.state==LabMateEvidenceCapturing);
    assert(!labmate_evidence_session_begin(&s,LabMateSnapshotFrequency,1,101,64000000U,true));cases++;
    assert(labmate_evidence_session_record(&s,2,4,0,100000U,0,0,640000U,0));cases++;
    assert(labmate_evidence_session_finish(&s,1100,true,&out));cases++;
    assert(out.quality==LabMateSnapshotValid && out.frequency_millihz==100000U);
    assert(out.ownership_released && out.capture_generation==1);
    assert(!labmate_evidence_session_finish(&s,1200,true,&out));cases++;
    LabMateDashboardStore store;
    labmate_dashboard_store_init(&store);
    assert(labmate_dashboard_store_ingest(&store,&out));cases++;
    assert(labmate_evidence_session_begin(&s,LabMateSnapshotFrequency,1,1500,64000000U,true));cases++;
    assert(s.last_generation==2U);
    assert(!labmate_evidence_session_record(&s,0,0,0,0,0,0,0,0));cases++;
    assert(!labmate_evidence_session_record(&s,2,4,0,100000U,0,0,0,0));cases++;
    assert(labmate_evidence_session_finish(&s,2500,true,&out));cases++;
    assert(out.quality==LabMateSnapshotInvalid);
    assert(labmate_dashboard_store_ingest(&store,&out));cases++;
    assert(!labmate_dashboard_store_read_measurement(&store,LabMateSnapshotFrequency,&out));cases++;
    assert(labmate_evidence_session_begin(&s,LabMateSnapshotPulse,3,3000,64000000U,true));cases++;
    assert(labmate_evidence_session_record(&s,2,4,0,0,32000,32000,64000,500));cases++;
    assert(labmate_evidence_session_finish(&s,3500,false,&out));cases++;
    assert(out.quality==LabMateSnapshotBusy && !out.ownership_released);
    assert(s.state==LabMateEvidenceReleaseFault);
    assert(!labmate_evidence_session_begin(&s,LabMateSnapshotPulse,3,4000,64000000U,true));cases++;
    labmate_evidence_session_init(&s);
    assert(labmate_evidence_session_begin(&s,LabMateSnapshotPulse,3,100,64000000U,true));cases++;
    assert(labmate_evidence_session_record(&s,1,2,0,0,32000,32000,64000,500));cases++;
    assert(!labmate_evidence_session_record(&s,1,2,0,0,32000,32000,64000,500));cases++;
    assert(labmate_evidence_session_finish(&s,150,true,&out));cases++;
    assert(out.quality==LabMateSnapshotInvalid);
    labmate_evidence_session_init(&s);
    assert(labmate_evidence_session_begin(&s,LabMateSnapshotPulse,3,200,64000000U,true));cases++;
    assert(labmate_evidence_session_record(&s,1,2,0,0,32000,32000,64000,500));cases++;
    assert(labmate_evidence_session_finish(&s,199,true,&out));cases++;
    assert(out.quality==LabMateSnapshotClockUnsafe);
    labmate_evidence_session_init(&s);
    assert(labmate_evidence_session_begin(&s,LabMateSnapshotPulse,3,100,64000000U,true));cases++;
    assert(labmate_evidence_session_record(&s,1,2,0,0,32000,32000,64000,500));cases++;
    assert(labmate_evidence_session_finish(&s,150,true,&out));cases++;
    assert(out.quality==LabMateSnapshotValid && out.frequency_millihz==1000000);
    for(unsigned pin=0;pin<8;pin++) {
        labmate_evidence_session_init(&s);
        const bool wanted=(pin==0||pin==1||pin==3||pin==5);
        const bool got=labmate_evidence_session_begin(&s,LabMateSnapshotPulse,(uint8_t)pin,1,64000000U,true);
        assert(got==wanted);
        cases++;
    }
    labmate_evidence_session_init(&s);
    s.last_generation=UINT32_MAX;
    assert(!labmate_evidence_session_begin(&s,LabMateSnapshotFrequency,1,100,64000000U,true));cases++;
    /* Rejection after a good value must never leak it as valid. */
    labmate_evidence_session_init(&s);
    assert(labmate_evidence_session_begin(&s,LabMateSnapshotFrequency,4,20,64000000U,true));cases++;
    assert(labmate_evidence_session_record(&s,1,2,0,400000U,0,0,0,0));cases++;
    assert(!labmate_evidence_session_record(&s,2,1,0,400000U,0,0,0,0));cases++;
    assert(labmate_evidence_session_finish(&s,40,true,&out));cases++;
    assert(out.quality==LabMateSnapshotInvalid);
    printf("Phase2C evidence lifecycle PASS: %u cases\n",cases);
    return 0;
}
