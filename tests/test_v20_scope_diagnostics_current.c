/* Map historical measured-cycle/gap/rejection cases to CURRENT production
 * metrics + period spread + Doctor symptoms. MAD no longer exists; it is
 * explicitly retired in the coverage ledger, never emulated by this test. */
#include "labmate_scope_compare.h"
#include "labmate_scope_period_stats.h"
#include "labmate_doctor_symptoms.h"
#include <assert.h>
#include <stdio.h>

static void edges_from_periods(LabMateScopeEdge* e,const uint32_t* periods,unsigned n) {
    unsigned i=0;uint32_t tick=100;
    e[i++]=(LabMateScopeEdge){.tick=tick,.delta_ticks=0,.high=true};
    for(unsigned p=0;p<n;p++) {
        const uint32_t high=periods[p]/2U,low=periods[p]-high;
        tick+=high;e[i++]=(LabMateScopeEdge){.tick=tick,.delta_ticks=high,.high=false};
        tick+=low;e[i++]=(LabMateScopeEdge){.tick=tick,.delta_ticks=low,.high=true};
    }
}
static LabMateDoctorSymptomReport analyze(const LabMateScopeEdge* e,uint16_t n) {
    LabMateDoctorSymptomReport report;
    const LabMateDoctorSymptomConfig cfg=labmate_doctor_symptom_defaults();
    const LabMateDoctorSymptomInput in={.edges=e,.count=n,.timebase_hz=64000000U,
        .initial_level=false,.last_level=n&&e?e[n-1U].high:false,
        .window_ms=1000U,.end_reason=LabMateSymptomEndUserStop};
    assert(labmate_doctor_symptoms_analyze(&in,&cfg,&report));
    return report;
}
int main(void) {
    LabMateScopeEdge e[11]={0};const uint32_t uniform[]={1000,1000,1000,1000};
    edges_from_periods(e,uniform,4);
    LabMateScopeMetrics m=labmate_scope_metrics_from_edges(e,9,64000000U);
    LabMateScopePeriodStats p;
    assert(m.status==LabMateScopeMetricsReady&&m.completed_cycles==4U);
    assert(labmate_scope_period_stats(&m,&p));
    assert(p.mean_period_ticks==1000U&&p.spread_permille==0U);
    LabMateDoctorSymptomReport r=analyze(e,9);
    assert(r.status==LabMateSymptomReady&&r.flags==0U&&r.gap_count==0U);
    const uint32_t gap[]={1000,1000,2000,1000};edges_from_periods(e,gap,4);
    m=labmate_scope_metrics_from_edges(e,9,64000000U);
    assert(labmate_scope_period_stats(&m,&p));
    assert(p.mean_period_ticks==1250U&&p.min_period_ticks==1000U&&p.max_period_ticks==2000U);
    assert(p.spread_permille==800U);
    r=analyze(e,9);
    assert(r.status==LabMateSymptomReady&&(r.flags&LABMATE_SYMPTOM_MISSING_PULSE));
    assert(r.gap_count==2U&&r.worst_gap_permille==2000U);
    e[4].high=false;
    m=labmate_scope_metrics_from_edges(e,9,64000000U);
    assert(m.status==LabMateScopeMetricsInvalid&&!labmate_scope_period_stats(&m,&p));
    r=analyze(e,9);assert(r.status==LabMateSymptomUnsafe&&r.flags==0U);
    edges_from_periods(e,uniform,4);e[4].delta_ticks=0;
    m=labmate_scope_metrics_from_edges(e,9,64000000U);
    assert(m.status==LabMateScopeMetricsInvalid&&!labmate_scope_period_stats(&m,&p));
    r=analyze(e,9);assert(r.status==LabMateSymptomUnsafe&&r.flags==0U);
    edges_from_periods(e,uniform,4);
    m=labmate_scope_metrics_from_edges(e,9,0U);
    assert(m.status==LabMateScopeMetricsClockInvalid&&!labmate_scope_period_stats(&m,&p));
    m=labmate_scope_metrics_from_edges(e,2,64000000U);
    assert(m.status==LabMateScopeMetricsInsufficient&&!labmate_scope_period_stats(&m,&p));
    r=analyze(e,2);assert(r.status==LabMateSymptomInsufficient&&r.flags==0U);
    m=labmate_scope_metrics_from_edges(NULL,9,64000000U);
    assert(m.status==LabMateScopeMetricsInvalid&&!labmate_scope_period_stats(&m,&p));
    r=analyze(NULL,9);assert(r.status==LabMateSymptomUnsafe&&r.flags==0U);
    const LabMateDoctorSymptomConfig cfg=labmate_doctor_symptom_defaults();
    const LabMateDoctorSymptomInput in={.edges=e,.count=9};
    assert(!labmate_doctor_symptoms_analyze(&in,&cfg,NULL));
    assert(!labmate_scope_period_stats(NULL,&p)&&!labmate_scope_period_stats(&m,NULL));
    puts("E11 scope diagnostics current cycles/gap/invalid gates PASS; no retired MAD claim");
    return 0;
}
