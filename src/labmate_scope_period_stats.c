#include "labmate_scope_period_stats.h"
#include <stdint.h>
bool labmate_scope_period_stats(
    const LabMateScopeMetrics* m, LabMateScopePeriodStats* out) {
    if(!m || !out || m->status != LabMateScopeMetricsReady || m->truncated ||
       m->completed_cycles < 2U || !m->timebase_hz ||
       !m->min_period_ticks || !m->max_period_ticks ||
       m->max_period_ticks < m->min_period_ticks) return false;
    if(m->total_high_ticks > UINT64_MAX - m->total_low_ticks) return false;
    const uint64_t total = m->total_high_ticks + m->total_low_ticks;
    if(!total || total < m->completed_cycles) return false;
    const uint64_t mean =
        (total + m->completed_cycles / 2U) / m->completed_cycles;
    if(!mean || mean > UINT32_MAX ||
       mean < m->min_period_ticks || mean > m->max_period_ticks) return false;
    const uint64_t delta = (uint64_t)m->max_period_ticks - m->min_period_ticks;
    const uint64_t permille = (delta * 1000U + mean / 2U) / mean;
    if(permille > UINT32_MAX) return false;
    *out = (LabMateScopePeriodStats){
        .mean_period_ticks=(uint32_t)mean,
        .min_period_ticks=m->min_period_ticks,
        .max_period_ticks=m->max_period_ticks,
        .spread_permille=(uint32_t)permille,
        .completed_cycles=m->completed_cycles
    };
    return true;
}
