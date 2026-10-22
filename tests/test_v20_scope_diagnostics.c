#include "labmate_scope_diagnostics.h"
#include <assert.h>
#include <stdio.h>
static void edges_from_periods(
    LabMateScopeEdge* edges, const uint32_t* periods, unsigned count) {
    unsigned index=0;
    uint32_t tick=100;
    edges[index++]=(LabMateScopeEdge){.tick=tick,.delta_ticks=0,.high=true};
    for(unsigned i=0;i<count;i++) {
        const uint32_t high=periods[i]/2U, low=periods[i]-high;
        tick+=high;
        edges[index++]=(LabMateScopeEdge){.tick=tick,.delta_ticks=high,.high=false};
        tick+=low;
        edges[index++]=(LabMateScopeEdge){.tick=tick,.delta_ticks=low,.high=true};
    }
}
int main(void) {
    LabMateScopeEdge e[11]={0};
    const uint32_t uniform[]={1000,1000,1000,1000};
    LabMateScopeDiagnostics a={0};
    edges_from_periods(e,uniform,4);
    assert(labmate_scope_diagnostics_compute(e,9,64000000U,&a));
    assert(a.valid&&a.complete_cycles==4&&a.mean_ticks==1000);
    assert(a.mean_abs_deviation_ticks==0 && a.spread_permille==0);
    assert(!a.gap_suspected);
    const uint32_t gap[]={1000,1000,2000,1000};
    edges_from_periods(e,gap,4);
    assert(labmate_scope_diagnostics_compute(e,9,64000000U,&a));
    assert(a.gap_suspected && a.min_ticks==1000 && a.max_ticks==2000);
    assert(a.mean_ticks==1250 && a.mean_abs_deviation_ticks==375);
    e[4].high=true;
    assert(!labmate_scope_diagnostics_compute(e,9,64000000U,&a));
    assert(!a.valid);
    edges_from_periods(e,uniform,4);
    e[4].delta_ticks=0;
    assert(!labmate_scope_diagnostics_compute(e,9,64000000U,&a));
    assert(!labmate_scope_diagnostics_compute(e,9,0U,&a));
    assert(!labmate_scope_diagnostics_compute(e,2,64000000U,&a));
    assert(!labmate_scope_diagnostics_compute(NULL,9,64000000U,&a));
    assert(!labmate_scope_diagnostics_compute(e,9,64000000U,NULL));
    puts("V20 SCOPE DIAGNOSTICS PASS: measured cycles, MAD, gap suspicion, invalid veto");
    return 0;
}
