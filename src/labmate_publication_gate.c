#include "labmate_publication_gate.h"
#include <limits.h>
#include <string.h>

void labmate_publication_gate_init(LabMatePublicationGate* g) {
    if(g) memset(g, 0, sizeof(*g));
}

static bool path_and_pin_valid(LabMatePublicationPath path, uint8_t pin) {
    switch(path) {
    case LabMatePublicationFrequencyLow: return pin == 1U; /* PC1 EXTI1 */
    case LabMatePublicationFrequencyHigh: return pin == 4U; /* PB3 TIM2 */
    case LabMatePublicationPulse:
        return pin == 0U || pin == 1U || pin == 3U || pin == 5U;
    default: return false;
    }
}

bool labmate_publication_gate_begin(
    LabMatePublicationGate* g, LabMatePublicationPath path, uint8_t pin,
    uint32_t start_ms, bool ownership_confirmed) {
    if(!g || g->active || g->poisoned || !ownership_confirmed ||
       !path_and_pin_valid(path, pin)) return false;
    g->path = path;
    g->pin_index = pin;
    g->start_ms = start_ms;
    g->previous_ms = start_ms;
    g->previous_edges = 0U;
    g->accepted_publications = 0U;
    g->active = true;
    return true;
}

static bool candidate_consistent(const LabMatePublicationGate* g,
                                 const LabMatePublicationCandidate* e) {
    if(e->frequency_millihz == 0U) return false;
    switch(g->path) {
    case LabMatePublicationFrequencyLow:
        return e->period_ticks != 0U && e->high_ticks == 0U &&
               e->low_ticks == 0U && e->duty_permille == 0U;
    case LabMatePublicationFrequencyHigh:
        /* Native TIM2 computes frequency from measured gate edges/time.
         * It has no per-edge CPU-cycle period to report. */
        return e->period_ticks == 0U && e->high_ticks == 0U &&
               e->low_ticks == 0U && e->duty_permille == 0U;
    case LabMatePublicationPulse: {
        if(!e->period_ticks || e->duty_permille > 1000U ||
           (uint64_t)e->high_ticks + e->low_ticks != e->period_ticks) return false;
        const uint32_t duty=(uint32_t)(((uint64_t)e->high_ticks * 1000U +
                                       e->period_ticks / 2U) / e->period_ticks);
        return e->duty_permille == duty;
    }
    default: return false;
    }
}

LabMatePublicationResult labmate_publication_gate_observe(
    LabMatePublicationGate* g, const LabMatePublicationCandidate* e) {
    if(!g || !e || !g->active || g->poisoned) return LabMatePublicationFault;
    /* Missing clock safety invalidates provenance even while waiting. */
    if(!e->native_clock_safe) {
        g->poisoned = true;
        return LabMatePublicationFault;
    }
    if(!e->native_publication_confirmed) return LabMatePublicationWait;
    const uint32_t minimum = g->path == LabMatePublicationPulse ? 2U : 1U;
    const uint32_t initial = g->path == LabMatePublicationPulse ? 3U : 2U;
    const bool bad = e->observed_at_ms <= g->previous_ms ||
        e->cumulative_edges < initial ||
        e->cumulative_edges <= g->previous_edges ||
        (g->accepted_publications > 0U &&
          e->cumulative_edges - g->previous_edges < minimum) ||
        g->accepted_publications == UINT32_MAX || !candidate_consistent(g, e);
    if(bad) {
        g->poisoned = true;
        return LabMatePublicationFault;
    }
    ++g->accepted_publications;
    g->previous_edges = e->cumulative_edges;
    g->previous_ms = e->observed_at_ms;
    return LabMatePublicationAccepted;
}
