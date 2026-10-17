#include "labmate_scope_pair.h"
#include <assert.h>
#include <stdio.h>

static LabMateScopeMetrics sample(uint64_t f, uint16_t duty) {
    return (LabMateScopeMetrics) {
        .status=LabMateScopeMetricsReady, .completed_cycles=3,
        .edge_count=7, .timebase_hz=64000000U,
        .frequency_millihz=f, .duty_permille=duty,
        .min_period_ticks=64000U, .max_period_ticks=64000U,
    };
}
static void sequential_a_then_b(void) {
    LabMateScopePair p={0};
    LabMateScopeMetrics a=sample(100000U,500U), b=sample(1000000U,250U);
    assert(!labmate_scope_pair_save_b(&p,&b,1U));
    assert(p.notice==LabMateScopePairNeedA && !p.has_b);
    assert(labmate_scope_pair_save_a(&p,&a,10U));
    assert(p.has_a && !p.has_b && p.generation_a==10U);
    assert(!labmate_scope_pair_save_b(&p,&b,10U));
    assert(p.notice==LabMateScopePairNeedFreshB);
    assert(!labmate_scope_pair_save_b(&p,&b,9U)); /* stale B */
    assert(labmate_scope_pair_save_b(&p,&b,11U));
    assert(p.has_a && p.has_b && p.delta.comparable);
    assert(p.delta.frequency_delta_millihz==900000);
    assert(p.delta.duty_delta_permille==-250);
    assert(!labmate_scope_pair_save_b(&p,&b,11U)); /* duplicate B */
    /* New A invalidates old B and any old delta. */
    assert(labmate_scope_pair_save_a(&p,&b,12U));
    assert(p.has_a && !p.has_b && !p.delta.comparable);
    assert(p.generation_a==12U && p.generation_b==0U);
    assert(!labmate_scope_pair_save_b(&p,&a,11U));
    assert(labmate_scope_pair_save_b(&p,&a,13U));
    assert(p.delta.frequency_delta_millihz==-900000);
    assert(p.delta.duty_delta_permille==250);
}
static void bad_data_cannot_overwrite_good_reference(void) {
    LabMateScopePair p={0};
    LabMateScopeMetrics a=sample(100000U,500U), broken=a;
    assert(labmate_scope_pair_save_a(&p,&a,3U));
    broken.status=LabMateScopeMetricsInsufficient;
    assert(!labmate_scope_pair_save_a(&p,&broken,4U));
    assert(p.generation_a==3U && p.has_a && !p.has_b);
    broken=a; broken.timebase_hz=0U;
    assert(!labmate_scope_pair_save_b(&p,&broken,4U));
    broken=a; broken.edge_count=2U;
    assert(!labmate_scope_pair_save_b(&p,&broken,4U));
    broken=a; broken.duty_permille=1001U;
    assert(!labmate_scope_pair_save_b(&p,&broken,4U));
    broken=a; broken.min_period_ticks=0U;
    assert(!labmate_scope_pair_save_b(&p,&broken,4U));
    broken=a; broken.frequency_millihz=0U;
    assert(!labmate_scope_pair_save_b(&p,&broken,4U));
    assert(!labmate_scope_pair_save_b(&p,&a,0U));
    assert(p.has_a && !p.has_b && p.generation_a==3U);
    assert(!labmate_scope_pair_save_a(NULL,&a,4U));
    labmate_scope_pair_reset(&p);
    assert(!p.has_a && !p.has_b && !p.delta.comparable);
}
int main(void) {
    sequential_a_then_b();
    bad_data_cannot_overwrite_good_reference();
    puts("v1.9 sequential A/B reference state, stale-run and invalid-data PASS");
    return 0;
}
