#include "labmate_pulse_pair_audit.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

static bool note(LabMatePulsePairAudit* a, bool high, bool low,
                 uint32_t hi, uint32_t lo, uint32_t edges) {
    return labmate_pulse_pair_note(a,high,low,true,true,hi,lo,edges);
}
int main(void) {
    unsigned cases=0U;
    LabMatePulsePairAudit a={0};
    LabMatePulsePairObservation s={0};
    assert(!labmate_pulse_pair_copy_locked(NULL,&s));cases++;
    assert(!labmate_pulse_pair_copy_locked(&a,NULL));cases++;
    labmate_pulse_pair_reset(NULL);
    labmate_pulse_pair_discard_partial(NULL);
    assert(!labmate_pulse_pair_note(NULL,true,true,true,true,100U,200U,3U));cases++;
    labmate_pulse_pair_reset(&a);
    assert(!a.pairs && !a.fresh_high && !a.fresh_low && !a.exhausted);cases++;
    /* Independent normal 16-width averages: only HIGH is new. */
    assert(!note(&a,true,false,100U,200U,32U));
    assert(a.fresh_high && !a.fresh_low && a.pairs==0U);cases++;
    /* Completing LOW yields one true paired publication. */
    assert(note(&a,false,true,100U,200U,33U));
    assert(a.pairs==1U && a.last_pair_edges==33U &&
           a.last_high_cycles==100U && a.last_low_cycles==200U);
    assert(!a.fresh_high && !a.fresh_low);cases++;
    assert(labmate_pulse_pair_copy_locked(&a,&s));
    assert(s.pairs==1U && s.edges==33U && s.high_cycles==100U && s.low_cycles==200U);cases++;
    /* A new LOW without a new HIGH cannot repeat the previous pair. */
    assert(!note(&a,false,true,100U,201U,34U));
    assert(a.pairs==1U && a.fresh_low);cases++;
    assert(note(&a,true,false,101U,201U,35U));
    assert(a.pairs==2U && a.last_pair_edges==35U);cases++;
    /* A smoothing-mode transition may not combine old and new halves. */
    assert(!note(&a,true,false,101U,202U,36U));
    labmate_pulse_pair_discard_partial(&a);
    assert(!note(&a,false,true,110U,210U,37U));
    assert(a.pairs==2U);cases++;
    /* Wide 128/128 window completes both phases simultaneously. */
    labmate_pulse_pair_discard_partial(&a);
    assert(note(&a,true,true,120U,220U,38U));
    assert(a.pairs==3U && a.last_high_cycles==120U && a.last_low_cycles==220U);cases++;
    /* Stale-signal reset discards partial updates, not generation history. */
    assert(!note(&a,true,false,120U,220U,39U));
    labmate_pulse_pair_discard_partial(&a);
    assert(!note(&a,false,true,121U,221U,40U));
    assert(a.pairs==3U);cases++;
    /* Repeated valid flags cannot synthesize a new pair. */
    labmate_pulse_pair_discard_partial(&a);
    for(unsigned i=0;i<128U;++i) {
        assert(!note(&a,false,false,100U,200U,41U+i));
        cases++;
    }
    assert(a.pairs==3U);
    /* The two phases must both be valid at publication time. */
    labmate_pulse_pair_reset(&a);
    assert(!labmate_pulse_pair_note(&a,true,false,true,false,100U,200U,3U));
    assert(!labmate_pulse_pair_note(&a,false,true,true,false,100U,200U,4U));
    assert(a.exhausted && !a.pairs);cases++;
    labmate_pulse_pair_reset(&a);
    assert(!note(&a,true,false,100U,200U,3U));
    assert(!note(&a,false,true,0U,200U,4U));
    assert(a.exhausted);cases++;
    labmate_pulse_pair_reset(&a);
    assert(!note(&a,true,false,UINT32_MAX,1U,3U));
    assert(!note(&a,false,true,UINT32_MAX,1U,4U));
    assert(a.exhausted);cases++;
    labmate_pulse_pair_reset(&a);
    assert(!note(&a,true,false,100U,200U,3U));
    assert(!note(&a,false,true,100U,200U,0U));
    assert(a.exhausted);cases++;
    labmate_pulse_pair_reset(&a);
    assert(!note(&a,true,false,100U,200U,3U));
    assert(note(&a,false,true,100U,200U,4U));
    assert(!note(&a,true,false,100U,200U,5U));
    assert(!note(&a,false,true,100U,200U,4U));
    assert(a.exhausted);cases++;
    labmate_pulse_pair_reset(&a);
    a.pairs=UINT32_MAX;
    assert(!note(&a,true,false,100U,200U,10U));
    assert(!note(&a,false,true,100U,200U,11U));
    assert(a.exhausted && a.pairs==UINT32_MAX);
    assert(!note(&a,true,true,100U,200U,12U));cases++;
    /* Long-pulse updates may each arrive separately and still form a pair. */
    labmate_pulse_pair_reset(&a);
    for(uint32_t i=1U;i<=1024U;++i) {
        assert(!note(&a,true,false,100U+i,200U+i,3U*i));
        assert(note(&a,false,true,100U+i,200U+i,3U*i+1U));
        assert(a.pairs==i);
        cases++;
    }
    assert(labmate_pulse_pair_copy_locked(&a,&s) && s.pairs==1024U);
    assert(s.edges==3073U && s.high_cycles==1124U && s.low_cycles==1224U);cases++;
    printf("Phase2J Pulse paired HIGH/LOW evidence PASS: %u scenarios\n",cases);
    return 0;
}
