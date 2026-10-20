#include "labmate_scope_pair.h"
#include <string.h>

void labmate_scope_pair_reset(LabMateScopePair* p) {
    if(p) memset(p, 0, sizeof(*p));
}

static bool valid(const LabMateScopeMetrics* m, uint32_t generation) {
    return generation != 0U && m &&
        m->status == LabMateScopeMetricsReady && !m->truncated &&
        m->completed_cycles != 0U &&
        m->edge_count >= 3U && m->edge_count <= LABMATE_SCOPE_MAX_EDGES &&
        m->timebase_hz != 0U && m->duty_permille <= 1000U &&
        m->frequency_millihz != 0U &&
        /* Two real transitions are required per cycle, so more than half
         * the edge-counter clock rate is physically impossible. */
        m->frequency_millihz <= (uint64_t)m->timebase_hz * 500U &&
        m->min_period_ticks >= 2U &&
        m->max_period_ticks >= m->min_period_ticks;
}

bool labmate_scope_pair_save_a(
    LabMateScopePair* p, const LabMateScopeMetrics* m, uint32_t gen) {
    if(!p) return false;
    if(!valid(m, gen)) {
        p->notice = LabMateScopePairInvalidSample;
        return false;
    }
    p->a = *m;
    p->has_a = true;
    p->generation_a = gen;
    p->has_b = false;
    p->generation_b = 0U;
    p->b = (LabMateScopeMetrics){0};
    p->delta = (LabMateScopeCompare){0};
    p->notice = LabMateScopePairSavedA;
    return true;
}

bool labmate_scope_pair_save_b(
    LabMateScopePair* p, const LabMateScopeMetrics* m, uint32_t gen) {
    if(!p) return false;
    if(!p->has_a) {
        p->notice = LabMateScopePairNeedA;
        return false;
    }
    /* This rejects saving A twice as B and a stale/pre-reference sample.
     * Deliberately fail-closed after a rare uint32 generation wrap. */
    if(gen <= p->generation_a || (p->has_b && gen == p->generation_b)) {
        p->notice = LabMateScopePairNeedFreshB;
        return false;
    }
    if(!valid(m, gen)) {
        p->notice = LabMateScopePairInvalidSample;
        return false;
    }
    LabMateScopeCompare comparison = labmate_scope_compare_metrics(&p->a, m);
    if(!comparison.comparable) {
        p->notice = LabMateScopePairInvalidSample;
        return false;
    }
    p->b = *m;
    p->delta = comparison;
    p->generation_b = gen;
    p->has_b = true;
    p->notice = LabMateScopePairSavedB;
    return true;
}
