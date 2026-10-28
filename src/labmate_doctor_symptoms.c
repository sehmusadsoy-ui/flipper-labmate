#include "labmate_doctor_symptoms.h"
#include "labmate_scope_compare.h"
#include "labmate_scope_period_stats.h"
#include <stdio.h>
#include <string.h>

#define SYMPTOM_MIN_RUNT_MEDIAN_TICKS 4U

LabMateDoctorSymptomConfig labmate_doctor_symptom_defaults(void) {
    return (LabMateDoctorSymptomConfig){
        .stuck_min_window_ms = 1000U,
        .gap_ratio_permille = 1750U,
        .runt_ratio_permille = 250U,
        .spread_threshold_permille = 100U,
        .min_intervals_per_level = 3U,
        .min_cycles_for_spread = 4U,
    };
}

static bool symptom_config_valid(const LabMateDoctorSymptomConfig* c) {
    return c->stuck_min_window_ms > 0U &&
           c->gap_ratio_permille > 1000U &&
           c->runt_ratio_permille > 0U && c->runt_ratio_permille < 1000U &&
           c->spread_threshold_permille > 0U &&
           c->min_intervals_per_level >= 2U &&
           c->min_cycles_for_spread >= 2U;
}

/* edge i (i >= 1) ends an interval that was spent at the level OPPOSITE to
 * the level after the edge. Edge 0 only starts the first (unmeasured) one. */
static bool interval_has_level(
    const LabMateScopeEdge* e, uint16_t i, bool level_high) {
    return i >= 1U && e[i].high == !level_high;
}

static uint16_t count_intervals(
    const LabMateScopeEdge* e, uint16_t n, bool level_high) {
    uint16_t cnt = 0U;
    for(uint16_t i = 1U; i < n; ++i)
        if(interval_has_level(e, i, level_high)) ++cnt;
    return cnt;
}

/* Lower median by rank, O(n^2) but n <= 256 and no scratch memory. */
static uint32_t median_interval(
    const LabMateScopeEdge* e, uint16_t n, bool level_high, uint16_t cnt) {
    if(!cnt) return 0U;
    const uint16_t k = (uint16_t)((cnt - 1U) / 2U);
    for(uint16_t i = 1U; i < n; ++i) {
        if(!interval_has_level(e, i, level_high)) continue;
        const uint32_t v = e[i].delta_ticks;
        uint16_t less = 0U, equal = 0U;
        for(uint16_t j = 1U; j < n; ++j) {
            if(!interval_has_level(e, j, level_high)) continue;
            if(e[j].delta_ticks < v) ++less;
            else if(e[j].delta_ticks == v) ++equal;
        }
        if(less <= k && k < (uint16_t)(less + equal)) return v;
    }
    return 0U;
}

static bool input_consistent(const LabMateDoctorSymptomInput* in) {
    if(in->count > LABMATE_SCOPE_MAX_EDGES) return false;
    if(in->count == 0U) return in->last_level == in->initial_level;
    if(!in->edges) return false;
    /* The first stored edge is a real transition away from the armed level,
     * every later edge alternates, and each stored interval is non-zero. */
    if(in->edges[0].high == in->initial_level) return false;
    for(uint16_t i = 1U; i < in->count; ++i) {
        if(in->edges[i].high == in->edges[i - 1U].high) return false;
        if(in->edges[i].delta_ticks == 0U) return false;
    }
    return in->edges[in->count - 1U].high == in->last_level;
}

bool labmate_doctor_symptoms_analyze(
    const LabMateDoctorSymptomInput* in,
    const LabMateDoctorSymptomConfig* cfg,
    LabMateDoctorSymptomReport* out) {
    if(!out) return false;
    *out = (LabMateDoctorSymptomReport){.status = LabMateSymptomNone};
    if(!in || !cfg || !symptom_config_valid(cfg)) return false;

    out->edge_count = in->count;
    out->window_ms = in->window_ms;
    if(in->clock_fault || in->truncated || !input_consistent(in)) {
        out->status = LabMateSymptomUnsafe;
        return true;
    }

    /* 1. No edge at all: only a long enough real window can say "held". */
    if(in->count == 0U) {
        const bool window_ok = in->window_ms >= cfg->stuck_min_window_ms &&
            (in->end_reason == LabMateSymptomEndNoTrigger ||
             in->end_reason == LabMateSymptomEndUserStop ||
             in->end_reason == LabMateSymptomEndDurationLimit);
        if(!window_ok) {
            out->status = LabMateSymptomInsufficient;
            return true;
        }
        out->status = LabMateSymptomReady;
        out->level_high = in->initial_level;
        out->flags = in->initial_level ? LABMATE_SYMPTOM_STUCK_HIGH
                                       : LABMATE_SYMPTOM_STUCK_LOW;
        return true;
    }

    uint16_t flags = 0U;
    /* 2. Activity that ended in silence: the line stayed at its last level. */
    if(in->end_reason == LabMateSymptomEndQuiet) {
        out->level_high = in->last_level;
        flags |= in->last_level ? LABMATE_SYMPTOM_STOPPED_HIGH
                                : LABMATE_SYMPTOM_STOPPED_LOW;
    }

    /* 3. Interval statistics per level (needs several real intervals). */
    out->high_intervals = count_intervals(in->edges, in->count, true);
    out->low_intervals = count_intervals(in->edges, in->count, false);
    const bool high_ok = out->high_intervals >= cfg->min_intervals_per_level;
    const bool low_ok = out->low_intervals >= cfg->min_intervals_per_level;
    if(high_ok)
        out->median_high_ticks =
            median_interval(in->edges, in->count, true, out->high_intervals);
    if(low_ok)
        out->median_low_ticks =
            median_interval(in->edges, in->count, false, out->low_intervals);

    for(uint16_t i = 1U; i < in->count; ++i) {
        const bool level_high = !in->edges[i].high;
        const bool ok = level_high ? high_ok : low_ok;
        const uint32_t med = level_high ? out->median_high_ticks
                                        : out->median_low_ticks;
        if(!ok || !med) continue;
        const uint64_t v1000 = (uint64_t)in->edges[i].delta_ticks * 1000U;
        if(v1000 >= (uint64_t)med * cfg->gap_ratio_permille) {
            if(out->gap_count < UINT16_MAX) ++out->gap_count;
            const uint64_t ratio = v1000 / med;
            if(ratio > out->worst_gap_permille)
                out->worst_gap_permille = ratio > UINT32_MAX ? UINT32_MAX
                                                             : (uint32_t)ratio;
        } else if(med >= SYMPTOM_MIN_RUNT_MEDIAN_TICKS &&
                  v1000 <= (uint64_t)med * cfg->runt_ratio_permille) {
            if(out->runt_count < UINT16_MAX) ++out->runt_count;
        }
    }
    if(out->gap_count) flags |= LABMATE_SYMPTOM_MISSING_PULSE;
    if(out->runt_count) flags |= LABMATE_SYMPTOM_RUNT_PULSE;

    /* 4. Period spread: descriptive, only when nothing else explains it. */
    if(in->timebase_hz) {
        const LabMateScopeMetrics m = labmate_scope_metrics_from_edges(
            in->edges, in->count, in->timebase_hz);
        LabMateScopePeriodStats stats;
        if(m.status == LabMateScopeMetricsReady && !m.truncated) {
            out->complete_cycles = m.completed_cycles;
            if(m.completed_cycles >= cfg->min_cycles_for_spread &&
               labmate_scope_period_stats(&m, &stats)) {
                out->spread_permille = stats.spread_permille;
                if(!(flags & (LABMATE_SYMPTOM_MISSING_PULSE |
                              LABMATE_SYMPTOM_RUNT_PULSE)) &&
                   stats.spread_permille > cfg->spread_threshold_permille)
                    flags |= LABMATE_SYMPTOM_PERIOD_SPREAD;
            }
        }
    }

    out->flags = flags;
    /* "No anomaly seen" must be backed by enough real intervals on both
     * levels; fewer edges are INSUFFICIENT, never a silent pass. */
    if(!flags && !(high_ok && low_ok)) {
        out->status = LabMateSymptomInsufficient;
        return true;
    }
    out->status = LabMateSymptomReady;
    return true;
}

static unsigned clamp99(unsigned v) { return v > 99U ? 99U : v; }

static void text_set(char* dst, size_t cap, const char* src) {
    (void)snprintf(dst, cap, "%s", src);
}

void labmate_doctor_symptom_text(
    const LabMateDoctorSymptomReport* r, LabMateDoctorSymptomText* t) {
    if(!t) return;
    memset(t, 0, sizeof(*t));
    if(!r || r->status == LabMateSymptomNone) {
        text_set(t->finding, sizeof(t->finding), "NO SCOPE CAPTURE");
        text_set(t->evidence, sizeof(t->evidence), "RUN SCOPE, THEN STOP");
        text_set(t->next_check, sizeof(t->next_check), "REOPEN DOCTOR");
        return;
    }
    if(r->status == LabMateSymptomUnsafe) {
        text_set(t->finding, sizeof(t->finding), "UNSAFE EVIDENCE");
        text_set(t->evidence, sizeof(t->evidence), "CLOCK/OVERFLOW");
        text_set(t->next_check, sizeof(t->next_check), "RETRY SAFELY");
        return;
    }
    if(r->status == LabMateSymptomInsufficient) {
        text_set(t->finding, sizeof(t->finding), "INSUFFICIENT");
        (void)snprintf(t->evidence, sizeof(t->evidence), "%u EDGES %lums",
                       clamp99(r->edge_count), (unsigned long)(r->window_ms % 100000UL));
        text_set(t->next_check, sizeof(t->next_check), "CAPTURE LONGER");
        return;
    }
    /* Ready: one primary finding by priority; evidence shows real counts. */
    const uint16_t f = r->flags;
    if(f & (LABMATE_SYMPTOM_STUCK_HIGH | LABMATE_SYMPTOM_STUCK_LOW)) {
        text_set(t->finding, sizeof(t->finding),
                 (f & LABMATE_SYMPTOM_STUCK_HIGH) ? "STUCK HIGH?" : "STUCK LOW?");
        (void)snprintf(t->evidence, sizeof(t->evidence), "NO EDGE %lums",
                       (unsigned long)(r->window_ms % 100000UL));
        text_set(t->next_check, sizeof(t->next_check), "CHECK SOURCE/WIRING");
    } else if(f & (LABMATE_SYMPTOM_STOPPED_HIGH | LABMATE_SYMPTOM_STOPPED_LOW)) {
        text_set(t->finding, sizeof(t->finding),
                 (f & LABMATE_SYMPTOM_STOPPED_HIGH) ? "SIGNAL STOPPED HIGH"
                                                    : "SIGNAL STOPPED LOW");
        (void)snprintf(t->evidence, sizeof(t->evidence), "HELD AFTER %u EDGES",
                       (unsigned)(r->edge_count > 999U ? 999U : r->edge_count));
        text_set(t->next_check, sizeof(t->next_check), "CHECK DRIVER/WIRING");
    } else if(f & (LABMATE_SYMPTOM_MISSING_PULSE | LABMATE_SYMPTOM_RUNT_PULSE)) {
        text_set(t->finding, sizeof(t->finding),
                 (f & LABMATE_SYMPTOM_MISSING_PULSE) ? "MISSING PULSE?"
                                                     : "RUNT PULSES");
        (void)snprintf(t->evidence, sizeof(t->evidence), "GAP%u RUNT%u CYC%u",
                       clamp99(r->gap_count), clamp99(r->runt_count),
                       clamp99(r->complete_cycles));
        text_set(t->next_check, sizeof(t->next_check),
                 (f & LABMATE_SYMPTOM_MISSING_PULSE) ? "CHECK DRIVE/CONTACT"
                                                     : "CHECK NOISE/BOUNCE");
    } else if(f & LABMATE_SYMPTOM_PERIOD_SPREAD) {
        const unsigned sp = r->spread_permille > 9999U ? 9999U : (unsigned)r->spread_permille;
        (void)snprintf(t->finding, sizeof(t->finding), "PERIOD SPREAD %u.%u%%",
                       sp / 10U, sp % 10U);
        (void)snprintf(t->evidence, sizeof(t->evidence), "%u CYCLES",
                       clamp99(r->complete_cycles));
        text_set(t->next_check, sizeof(t->next_check), "CHECK CLOCK/SUPPLY");
    } else {
        text_set(t->finding, sizeof(t->finding), "NO ANOMALY SEEN");
        (void)snprintf(t->evidence, sizeof(t->evidence), "%u CYC %u EDGES",
                       clamp99(r->complete_cycles),
                       (unsigned)(r->edge_count > 999U ? 999U : r->edge_count));
        text_set(t->next_check, sizeof(t->next_check), "TEST UNDER LOAD");
    }
}
