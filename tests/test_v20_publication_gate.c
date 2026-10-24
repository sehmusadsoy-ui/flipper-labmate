#include "labmate_publication_gate.h"
#include "labmate_snapshot_bridge.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

static LabMatePublicationCandidate valid(LabMatePublicationPath path,
                                          uint32_t at, uint32_t edges) {
    LabMatePublicationCandidate e={0};
    e.native_publication_confirmed=true;
    e.native_clock_safe=true;
    e.observed_at_ms=at;
    e.cumulative_edges=edges;
    e.frequency_millihz=1000000U;
    if(path == LabMatePublicationFrequencyLow) e.period_ticks=64000U;
    if(path == LabMatePublicationPulse) {
        e.period_ticks=64000U;e.high_ticks=32000U;e.low_ticks=32000U;
        e.duty_permille=500U;
    }
    return e;
}
static void expect_fault(LabMatePublicationPath path,
                         LabMatePublicationCandidate e) {
    LabMatePublicationGate g={0};
    assert(labmate_publication_gate_begin(&g,path,
       path==LabMatePublicationFrequencyLow?1U:
       path==LabMatePublicationFrequencyHigh?4U:0U,100U,true));
    assert(labmate_publication_gate_observe(&g,&e)==LabMatePublicationFault);
    assert(g.poisoned && g.accepted_publications==0U);
    assert(labmate_publication_gate_observe(&g,&e)==LabMatePublicationFault);
    assert(!labmate_publication_gate_begin(&g,path,g.pin_index,200U,true));
}
int main(void) {
    unsigned checks=0U;
    LabMatePublicationGate g={0};
    assert(!labmate_publication_gate_begin(NULL,LabMatePublicationPulse,1,100,true));checks++;
    for(unsigned path=0;path<3;path++)for(unsigned pin=0;pin<8;pin++) {
        labmate_publication_gate_init(&g);
        const bool legal=(path==0&&pin==1)||(path==1&&pin==4)||
                         (path==2&&(pin==0||pin==1||pin==3||pin==5));
        assert(labmate_publication_gate_begin(&g,(LabMatePublicationPath)path,
                                            (uint8_t)pin,100U,true)==legal);
        assert(g.active==legal);checks++;
    }
    for(unsigned path=0;path<3;path++) {
        labmate_publication_gate_init(&g);
        const uint8_t pin=path==0?1U:path==1?4U:0U;
        assert(!labmate_publication_gate_begin(&g,(LabMatePublicationPath)path,pin,100,false));checks++;
        assert(labmate_publication_gate_begin(&g,(LabMatePublicationPath)path,pin,100,true));
        assert(!labmate_publication_gate_begin(&g,(LabMatePublicationPath)path,pin,100,true));checks++;
        LabMatePublicationCandidate e=valid((LabMatePublicationPath)path,200U,4U);
        e.native_publication_confirmed=false;
        assert(labmate_publication_gate_observe(&g,&e)==LabMatePublicationWait);
        assert(g.accepted_publications==0U);checks++;
        e.native_publication_confirmed=true;
        assert(labmate_publication_gate_observe(&g,&e)==LabMatePublicationAccepted);
        assert(g.accepted_publications==1U&&g.previous_edges==4U);checks++;
        e.observed_at_ms=201U;
        e.cumulative_edges+=path==2?2U:1U;
        assert(labmate_publication_gate_observe(&g,&e)==LabMatePublicationAccepted);
        assert(g.accepted_publications==2U);checks++;
        assert(labmate_publication_gate_observe(&g,&e)==LabMatePublicationFault);
        assert(g.poisoned);checks++;
        e=valid((LabMatePublicationPath)path,100U,10U);
        expect_fault((LabMatePublicationPath)path,e);checks++;
        e=valid((LabMatePublicationPath)path,200U,1U);
        expect_fault((LabMatePublicationPath)path,e);checks++;
        e=valid((LabMatePublicationPath)path,200U,10U);e.frequency_millihz=0U;
        expect_fault((LabMatePublicationPath)path,e);checks++;
        e=valid((LabMatePublicationPath)path,200U,10U);e.native_clock_safe=false;
        expect_fault((LabMatePublicationPath)path,e);checks++;
        e=valid((LabMatePublicationPath)path,200U,10U);
        if(path==0)e.period_ticks=0U;
        if(path==1)e.period_ticks=1U;
        if(path==2)e.high_ticks=33000U;
        expect_fault((LabMatePublicationPath)path,e);checks++;
        labmate_publication_gate_init(&g);
        assert(labmate_publication_gate_begin(&g,(LabMatePublicationPath)path,pin,100U,true));
        e=valid((LabMatePublicationPath)path,200U,UINT32_MAX);
        assert(labmate_publication_gate_observe(&g,&e)==LabMatePublicationAccepted);checks++;
        e=valid((LabMatePublicationPath)path,201U,0U);
        assert(labmate_publication_gate_observe(&g,&e)==LabMatePublicationFault);
        assert(g.poisoned);checks++;
    }
    /* Pin policy must agree with Phase 2C snapshot bridge on all 8 pins. */
    for(unsigned pin=0;pin<8;pin++) {
        const bool frequency=(pin==1U || pin==4U);
        const bool pulse_allowed=(pin==0U||pin==1U||pin==3U||pin==5U);
        assert(labmate_snapshot_capture_pin_supported(LabMateSnapshotFrequency,(uint8_t)pin)==frequency);
        checks++;
        assert(labmate_snapshot_capture_pin_supported(LabMateSnapshotPulse,(uint8_t)pin)==pulse_allowed);
        checks++;
    }
    /* Pulse needs a second physical transition per further completed pair. */
    labmate_publication_gate_init(&g);
    assert(labmate_publication_gate_begin(&g,LabMatePublicationPulse,0,100,true));
    LabMatePublicationCandidate e=valid(LabMatePublicationPulse,200U,4U);
    assert(labmate_publication_gate_observe(&g,&e)==LabMatePublicationAccepted);
    e.observed_at_ms=201;e.cumulative_edges=5;
    assert(labmate_publication_gate_observe(&g,&e)==LabMatePublicationFault);checks++;
    printf("Phase2E native-publication admission PASS: %u boundary checks\n",checks);
    return checks==81U?0:1;
}
