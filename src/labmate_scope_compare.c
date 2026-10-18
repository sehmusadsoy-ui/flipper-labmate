#include "labmate_scope_compare.h"

LabMateScopeMetrics labmate_scope_metrics_from_edges(
    const LabMateScopeEdge* edges, uint16_t count, uint32_t timebase_hz) {
    LabMateScopeMetrics m = {.status = LabMateScopeMetricsInvalid,
                             .edge_count = count, .timebase_hz = timebase_hz};
    if(!timebase_hz) {
        m.status = LabMateScopeMetricsClockInvalid;
        return m;
    }
    if((count != 0U && !edges) || count > LABMATE_SCOPE_MAX_EDGES) return m;
    if(count < 3U) {
        m.status = LabMateScopeMetricsInsufficient;
        return m;
    }
    uint64_t observed_span = 0U;
    for(uint16_t i = 1U; i < count; ++i) {
        const uint32_t delta = edges[i].tick - edges[i - 1U].tick;
        if(!delta || delta > LABMATE_SCOPE_MAX_SAFE_DELTA ||
           delta != edges[i].delta_ticks || edges[i].high == edges[i - 1U].high)
            return m;
        observed_span += delta;
        /* DWT 32-bit half-wrap ambiguity is fatal, even if individual
         * intervals each appear short. Do NOT silently accept stale edges. */
        if(observed_span > LABMATE_SCOPE_MAX_SAFE_DELTA) return m;
    }
    const uint16_t first_rise = edges[0].high ? 0U : 1U;
    uint64_t total_period = 0U;
    for(uint16_t i = first_rise; (uint32_t)i + 2U < count; i += 2U) {
        /* The previous loop already proved all three alternating edges. */
        const uint32_t high_ticks = edges[i + 1U].delta_ticks;
        const uint32_t low_ticks = edges[i + 2U].delta_ticks;
        const uint32_t period = high_ticks + low_ticks;
        if(period < high_ticks || !period || period > LABMATE_SCOPE_MAX_SAFE_DELTA)
            return m;
        m.total_high_ticks += high_ticks;
        m.total_low_ticks += low_ticks;
        total_period += period;
        if(!m.completed_cycles || period < m.min_period_ticks)
            m.min_period_ticks = period;
        if(period > m.max_period_ticks) m.max_period_ticks = period;
        ++m.completed_cycles;
    }
    if(!m.completed_cycles) {
        m.status = LabMateScopeMetricsInsufficient;
        return m;
    }
    /* Each H-L-H cycle is individually observed. 64-bit sums avoid overflow
     * when a legal 256-edge history spans millions of CYCCNT ticks. */
    const uint64_t numerator = (uint64_t)timebase_hz * UINT64_C(1000) *
                               m.completed_cycles;
    m.frequency_millihz = (numerator + total_period / 2U) / total_period;
    m.duty_permille = (uint16_t)((m.total_high_ticks * UINT64_C(1000) +
                                 total_period / 2U) / total_period);
    m.status = LabMateScopeMetricsReady;
    return m;
}

LabMateScopeCompare labmate_scope_compare_metrics(
    const LabMateScopeMetrics* a, const LabMateScopeMetrics* b) {
    LabMateScopeCompare c = {0};
    if(!a || !b || a->status != LabMateScopeMetricsReady ||
       b->status != LabMateScopeMetricsReady || a->truncated || b->truncated ||
       !a->completed_cycles ||
       !b->completed_cycles || !a->timebase_hz || !b->timebase_hz ||
       a->duty_permille > 1000U || b->duty_permille > 1000U ||
       a->frequency_millihz > INT64_MAX || b->frequency_millihz > INT64_MAX)
        return c;
    c.comparable = true;
    c.frequency_delta_millihz = (int64_t)b->frequency_millihz -
                                (int64_t)a->frequency_millihz;
    c.duty_delta_permille = (int16_t)((int32_t)b->duty_permille -
                                    (int32_t)a->duty_permille);
    return c;
}
