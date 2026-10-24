#include "labmate_scope_diagnostics.h"
#include <stdint.h>
bool labmate_scope_diagnostics_compute(
    const LabMateScopeEdge* edges, uint16_t count, uint32_t hz,
    LabMateScopeDiagnostics* out) {
    if(!out) return false;
    *out=(LabMateScopeDiagnostics){0};
    if(!edges || count < 5U || count > LABMATE_SCOPE_MAX_EDGES || !hz) return false;
    const LabMateScopeMetrics m=labmate_scope_metrics_from_edges(edges,count,hz);
    if(m.status != LabMateScopeMetricsReady || m.truncated ||
       m.completed_cycles < 2U || m.min_period_ticks < 2U ||
       m.max_period_ticks < m.min_period_ticks ||
       m.total_high_ticks > UINT64_MAX - m.total_low_ticks) return false;
    const uint64_t total=m.total_high_ticks + m.total_low_ticks;
    const uint64_t mean=(total + m.completed_cycles/2U)/m.completed_cycles;
    if(!mean || mean > UINT32_MAX) return false;
    const uint64_t span=(uint64_t)m.max_period_ticks-m.min_period_ticks;
    const uint64_t spread=(span*1000U + mean/2U)/mean;
    if(spread > UINT32_MAX) return false;
    uint64_t abs_sum=0U;
    uint16_t near_min=0U, near_double=0U, cycles=0U;
    const uint16_t first=edges[0].high ? 0U : 1U;
    for(uint16_t i=first; (uint32_t)i+2U<count; i=(uint16_t)(i+2U)) {
        const uint64_t period=(uint64_t)edges[i+1U].delta_ticks +
                              edges[i+2U].delta_ticks;
        if(period < m.min_period_ticks || period > m.max_period_ticks)
            return false;
        abs_sum += period > mean ? period-mean : mean-period;
        if(period*100U <= (uint64_t)m.min_period_ticks*115U)
            ++near_min;
        if(period*10U >= (uint64_t)m.min_period_ticks*17U &&
           period*10U <= (uint64_t)m.min_period_ticks*23U)
            ++near_double;
        ++cycles;
    }
    if(cycles != m.completed_cycles) return false;
    const uint64_t mad=(abs_sum + cycles/2U)/cycles;
    if(mad > UINT32_MAX) return false;
    *out=(LabMateScopeDiagnostics){
        .valid=true,
        .complete_cycles=cycles,
        .min_ticks=m.min_period_ticks,
        .max_ticks=m.max_period_ticks,
        .mean_ticks=(uint32_t)mean,
        .mean_abs_deviation_ticks=(uint32_t)mad,
        .spread_permille=(uint32_t)spread,
        .gap_suspected=cycles>=4U && near_min>=3U && near_double>=1U,
    };
    return true;
}
