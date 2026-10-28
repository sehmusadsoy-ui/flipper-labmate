#include "labmate_doctor_panel.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    LabMateDoctorPanel p;
    LabMateDashboardStore s;
    labmate_doctor_panel_init(&p);
    labmate_dashboard_store_init(&s);
    assert(p.reference.frequency_millihz == 0U);
    assert(labmate_doctor_panel_assess(&p,&s).status == LabMateDoctorPanelSetReference);
    labmate_doctor_panel_move(&p,+1);
    labmate_doctor_panel_edit(&p,+1);
    assert(p.reference.frequency_millihz==1000U);
    assert(labmate_doctor_panel_assess(&p,&s).status == LabMateDoctorPanelNoData);
    labmate_doctor_panel_edit(&p,-1);
    assert(p.reference.frequency_millihz==0U);
    labmate_doctor_panel_step(&p);
    labmate_doctor_panel_edit(&p,+1);
    assert(p.reference.frequency_millihz==10000U);
    labmate_doctor_panel_step(&p);
    labmate_doctor_panel_step(&p);
    assert(p.frequency_step_hz==1000U);
    labmate_doctor_panel_move(&p,1);
    labmate_doctor_panel_edit(&p,-1);
    assert(p.reference.frequency_tolerance_permille==40U);
    labmate_doctor_panel_move(&p,1);
    labmate_doctor_panel_edit(&p,+1);
    assert(p.reference.expected_duty_permille==510U);
    labmate_doctor_panel_move(&p,1);
    labmate_doctor_panel_edit(&p,-1);
    assert(p.reference.duty_tolerance_permille==40U);
    labmate_doctor_panel_move(&p,1);
    for(unsigned i=0;i<200;i++) labmate_doctor_panel_edit(&p,-1);
    assert(p.reference.minimum_no_signal_window_ms==100U);
    labmate_doctor_panel_move(&p,1);
    assert(p.field==LabMateDoctorFieldSource);
    labmate_doctor_panel_edit(&p,+1);
    assert(p.source==LabMateSnapshotPulse);
    labmate_doctor_panel_edit(&p,-1);
    assert(p.source==LabMateSnapshotFrequency);
    /* UI Step 2 intentionally restricts the reference editor to the
     * two capture-backed sources. No hidden Scope/Monitor path. */
    labmate_doctor_panel_edit(&p,-1);
    assert(p.source==LabMateSnapshotPulse);
    labmate_doctor_panel_edit(&p,-1);
    assert(p.source==LabMateSnapshotFrequency);
    labmate_doctor_panel_edit(&p,+1);
    assert(p.source==LabMateSnapshotPulse);
    labmate_doctor_panel_edit(&p,+1);
    assert(p.source==LabMateSnapshotFrequency);
    assert(!strcmp(labmate_doctor_panel_status_text(NULL),"WAIT"));

    LabMateSnapshotV1 bad={0};
    bad.schema_version=LABMATE_SNAPSHOT_VERSION;
    bad.source=LabMateSnapshotFrequency;
    bad.pin_index=1;
    bad.capture_generation=1;
    bad.quality=LabMateSnapshotBusy;
    bad.observation_start_ms=100;
    bad.observation_end_ms=1100;
    bad.timebase_hz=64000000U;
    bad.ownership_released=false;
    assert(labmate_dashboard_store_ingest(&s,&bad));
    assert(labmate_doctor_panel_assess(&p,&s).status==LabMateDoctorPanelBusy);
    bad.capture_generation=2;
    bad.quality=LabMateSnapshotInvalid;
    assert(labmate_dashboard_store_ingest(&s,&bad));
    assert(labmate_doctor_panel_assess(&p,&s).status==LabMateDoctorPanelUnsafe);
    bad.capture_generation=3;
    bad.quality=LabMateSnapshotInsufficient;
    assert(labmate_dashboard_store_ingest(&s,&bad));
    assert(labmate_doctor_panel_assess(&p,&s).status==LabMateDoctorPanelInsufficient);
    assert(!labmate_doctor_panel_assess(NULL,&s).doctor.evidence_accepted);
    assert(!labmate_doctor_panel_assess(&p,NULL).doctor.evidence_accepted);
    puts("PHASE3B DOCTOR PANEL PASS: reference editing, fail-closed states, no synthetic evidence");
    return 0;
}
