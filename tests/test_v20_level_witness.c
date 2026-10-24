#include "labmate_level_witness.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    LabMateLevelWitness w;
    assert(labmate_level_begin(&w,1,true,1000,1000));
    for(unsigned tick=1100;tick<=2200;tick+=100)
        assert(labmate_level_observe(&w,1,true,tick,1000));
    labmate_level_finish(&w,1,true,2250,1000);
    assert(labmate_level_assess(&w,1000)==LabMateLevelSampledHigh);
    assert(labmate_level_assess(&w,1500)==LabMateLevelNoEvidence);
    assert(labmate_level_begin(&w,1,false,1000,1000));
    for(unsigned tick=1100;tick<=2200;tick+=100)
        assert(labmate_level_observe(&w,1,false,tick,1000));
    labmate_level_finish(&w,1,true,2250,1000);
    assert(labmate_level_assess(&w,1000)==LabMateLevelSampledLow);
    assert(labmate_level_begin(&w,1,true,1000,1000));
    for(unsigned tick=1100;tick<=2200;tick+=100)
        assert(labmate_level_observe(&w,1,tick!=1500,tick,1000));
    labmate_level_finish(&w,1,true,2250,1000);
    assert(labmate_level_assess(&w,1000)==LabMateLevelTransitions);
    assert(labmate_level_begin(&w,1,true,1000,1000));
    assert(!labmate_level_observe(&w,2,true,1100,1000));
    assert(labmate_level_assess(&w,100)==LabMateLevelNoEvidence);
    assert(labmate_level_begin(&w,1,true,1000,1000));
    assert(!labmate_level_observe(&w,1,true,1300,1000));
    assert(labmate_level_assess(&w,100)==LabMateLevelNoEvidence);
    assert(labmate_level_begin(&w,1,true,1000,1000));
    for(unsigned tick=1100;tick<=2200;tick+=100)
        assert(labmate_level_observe(&w,1,true,tick,1000));
    labmate_level_finish(&w,1,false,2250,1000);
    assert(labmate_level_assess(&w,1000)==LabMateLevelNoEvidence);
    assert(!labmate_level_begin(&w,8,true,1000,1000));
    assert(!labmate_level_begin(&w,1,true,1000,0));
    assert(labmate_level_assess(NULL,100)==LabMateLevelNoEvidence);
    puts("V20 LEVEL WITNESS PASS: sampled H/L, edges, gaps, pin, clock, release veto");
    return 0;
}
