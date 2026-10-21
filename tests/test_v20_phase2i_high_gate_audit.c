#include "labmate_high_gate_audit.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <limits.h>

static bool audited(LabMateHighGateAudit* a, uint32_t last, uint32_t edges,
                    uint32_t cycles, uint32_t clock_hz) {
    uint32_t measured=0U;
    const LabMateHighGateResult result=
        labmate_high_gate_evaluate(edges,cycles,clock_hz,&measured);
    return labmate_high_gate_audit_record(a,result,last,edges,cycles,measured);
}
int main(void) {
    unsigned cases=0U;
    LabMateHighGateAudit a={0};
    labmate_high_gate_audit_reset(&a);
    assert(!a.publications && !a.exhausted);cases++;
    assert(!labmate_high_gate_audit_record(NULL,LabMateHighGatePublish,50,32,6400000,320000));
    labmate_high_gate_audit_reset(NULL);cases++;

    /* Ordinary 100 ms TIM2 poll, no counter boundary: not an observation. */
    assert(!audited(&a,0,0,6400000U,64000000U));
    assert(a.publications==0U);cases++;

    /* Partial gate: fewer than 32 edges and less than three seconds. */
    assert(!audited(&a,31,31,6400000U,64000000U));
    assert(!a.publications);cases++;

    /* Three seconds with only one extra edge is not a valid gate. */
    assert(!audited(&a,1,1,192000000U,64000000U));
    assert(!a.publications);cases++;

    assert(audited(&a,32,32,6400000U,64000000U));
    assert(a.publications==1U && a.last_counter==32U);
    assert(a.last_gate_edges==32U && a.last_gate_cycles==6400000U);
    assert(a.last_frequency_millihz==320000U);cases++;

    /* A repeated TIM2 count is not another published gate, even if forged. */
    assert(!labmate_high_gate_audit_record(
        &a,LabMateHighGatePublish,32U,32U,6400000U,320000U));
    assert(a.publications==1U && !a.exhausted);cases++;

    /* Native NoSample and Wait verdicts never increment. */
    assert(!labmate_high_gate_audit_record(
        &a,LabMateHighGateNoSample,64U,32U,6400000U,320000U));
    assert(!labmate_high_gate_audit_record(
        &a,LabMateHighGateWait,64U,32U,6400000U,320000U));
    assert(a.publications==1U);cases++;

    /* 1 Hz low-rate PB3/TIM2 gate: native estimator needs ~3 seconds. */
    assert(audited(&a,35U,3U,192000000U,64000000U));
    assert(a.last_gate_edges==3U && a.last_frequency_millihz==1000U);
    assert(a.publications==2U);cases++;

    /* Malformed alleged Publish never enters the audit. */
    assert(!labmate_high_gate_audit_record(
        &a,LabMateHighGatePublish,64U,1U,6400000U,320000U));
    assert(!labmate_high_gate_audit_record(
        &a,LabMateHighGatePublish,64U,32U,0U,320000U));
    assert(!labmate_high_gate_audit_record(
        &a,LabMateHighGatePublish,64U,32U,6400000U,0U));
    assert(a.publications==2U);cases++;

    /* A hardware counter may wrap without faking a missing DWT period. */
    assert(audited(&a,0U,32U,6400000U,64000000U));
    assert(a.publications==3U && a.last_counter==0U);cases++;

    /* No successful gate due to unknown counter clock. */
    assert(!audited(&a,64U,32U,6400000U,0U));cases++;

    /* Wide deterministic publish matrix; polls are never counted. */
    uint32_t previous_count=0U;
    for(uint32_t i=1U;i<=1024U;++i) {
        const uint32_t edges=32U+(i%100U);
        const uint32_t next=previous_count+edges;
        assert(audited(&a,next,edges,6400000U,64000000U));
        assert(a.publications==3U+i && a.last_gate_edges==edges);
        previous_count=next;
        if((i%4U)==0U) {
            const uint32_t last=a.publications;
            assert(!audited(&a,next,0U,6400000U,64000000U));
            assert(a.publications==last);
        }
        cases++;
    }

    /* Near-overflow is accepted once; rollover gets permanently denied. */
    a.publications=UINT32_MAX-1U;
    assert(audited(&a,previous_count+32U,32U,6400000U,64000000U));
    assert(a.publications==UINT32_MAX);
    assert(!audited(&a,previous_count+64U,32U,6400000U,64000000U));
    assert(a.exhausted && a.publications==UINT32_MAX);
    assert(!audited(&a,previous_count+96U,32U,6400000U,64000000U));cases++;

    /* Only a verified NEW native acquisition may invoke this reset. */
    labmate_high_gate_audit_reset(&a);
    assert(a.publications==0U && !a.exhausted &&
           a.last_gate_cycles==0U && a.last_counter==0U);cases++;

    printf("Phase2I PB3/TIM2 accepted-gate audit PASS: %u test groups\n",cases);
    return cases==1039U?0:1;
}
