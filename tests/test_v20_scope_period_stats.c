#include "labmate_scope_period_stats.h"
#include <assert.h>
#include <stdio.h>
static LabMateScopeMetrics good(void) {
    return (LabMateScopeMetrics){
       .status=LabMateScopeMetricsReady,.completed_cycles=4,
       .timebase_hz=64000000,
       .min_period_ticks=900,.max_period_ticks=1100,
       .total_high_ticks=2000,.total_low_ticks=2000
    };
}
int main(void) {
    LabMateScopePeriodStats p={0};
    LabMateScopeMetrics m=good();
    assert(labmate_scope_period_stats(&m,&p));
    assert(p.completed_cycles==4&&p.mean_period_ticks==1000);
    assert(p.min_period_ticks==900&&p.max_period_ticks==1100);
    assert(p.spread_permille==200);
    m=good();m.status=LabMateScopeMetricsClockInvalid;
    assert(!labmate_scope_period_stats(&m,&p));
    m=good();m.truncated=true;assert(!labmate_scope_period_stats(&m,&p));
    m=good();m.completed_cycles=1;assert(!labmate_scope_period_stats(&m,&p));
    m=good();m.timebase_hz=0;assert(!labmate_scope_period_stats(&m,&p));
    m=good();m.min_period_ticks=0;assert(!labmate_scope_period_stats(&m,&p));
    m=good();m.max_period_ticks=500;assert(!labmate_scope_period_stats(&m,&p));
    m=good();m.total_high_ticks=UINT64_MAX;
    assert(!labmate_scope_period_stats(&m,&p));
    m=good();m.total_high_ticks=0;m.total_low_ticks=1;
    assert(!labmate_scope_period_stats(&m,&p));
    m=good();m.total_high_ticks=10000;m.total_low_ticks=10000;
    assert(!labmate_scope_period_stats(&m,&p));
    assert(!labmate_scope_period_stats(NULL,&p));
    assert(!labmate_scope_period_stats(&m,NULL));
    puts("V20 SCOPE PERIOD SPREAD HOST PASS: real-cycle mean, min/max, guarded spread");
    return 0;
}
