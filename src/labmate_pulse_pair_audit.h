#pragma once
/* Phase 2J: Pulse IRQ coherent HALF-WINDOW publication evidence.
 * Paired here means BOTH HIGH and LOW estimates were refreshed after the
 * prior pair. They can be independent 16-sample or long-pulse windows;
 * it does NOT claim both came from one physical cycle.
 * No GPIO, HAL, memory allocation, logging or resource release.
 */
#include <stdbool.h>
#include <stdint.h>
#include <limits.h>

typedef struct {
    volatile uint32_t pairs;
    volatile uint32_t last_pair_edges;
    volatile uint32_t last_high_cycles;
    volatile uint32_t last_low_cycles;
    volatile bool fresh_high;
    volatile bool fresh_low;
    volatile bool exhausted;
} LabMatePulsePairAudit;

typedef struct {
    uint32_t pairs;
    uint32_t edges;
    uint32_t high_cycles;
    uint32_t low_cycles;
    bool exhausted;
} LabMatePulsePairObservation;

/* Call only while real native callback delivery is disabled, after a
 * successful new Pulse IRQ lease/callback acquisition. */
static inline void labmate_pulse_pair_reset(LabMatePulsePairAudit* a) {
    if(!a) return;
    a->pairs=0U;
    a->last_pair_edges=0U;
    a->last_high_cycles=0U;
    a->last_low_cycles=0U;
    a->fresh_high=false;
    a->fresh_low=false;
    a->exhausted=false;
}

/* A switch between normal and wide averaging discards incomplete halves,
 * but it must NEVER roll back the publication counter or clear faults.
 * Also used for a confirmed stale-signal reset with IRQ excluded. */
static inline void labmate_pulse_pair_discard_partial(LabMatePulsePairAudit* a) {
    if(!a) return;
    a->fresh_high=false;
    a->fresh_low=false;
}

/* Called exactly once after processing each genuine IRQ transition.
 * "new_high/low" must be true ONLY after a completed phase estimate was
 * published. Both nonzero phase lengths, a fresh cumulative IRQ edge, and
 * no count overflow are required before advancing paired-publications.
 */
static inline bool labmate_pulse_pair_note(
    LabMatePulsePairAudit* a, bool new_high, bool new_low,
    bool high_valid, bool low_valid, uint32_t high_cycles,
    uint32_t low_cycles, uint32_t cumulative_edges) {
    if(!a || a->exhausted) return false;
    if(new_high) a->fresh_high=true;
    if(new_low) a->fresh_low=true;
    if(!a->fresh_high || !a->fresh_low) return false;
    if(!high_valid || !low_valid || !high_cycles || !low_cycles ||
       (uint64_t)high_cycles + low_cycles > UINT32_MAX ||
       cumulative_edges == 0U ||
       (a->pairs && cumulative_edges <= a->last_pair_edges) ||
       a->pairs == UINT32_MAX) {
        a->exhausted=true;
        return false;
    }
    ++a->pairs;
    a->last_pair_edges=cumulative_edges;
    a->last_high_cycles=high_cycles;
    a->last_low_cycles=low_cycles;
    a->fresh_high=false;
    a->fresh_low=false;
    return true;
}

/* Caller must mask the native Pulse IRQ for the entire copy. Never read
 * individual audit fields from an unprotected UI update. */
static inline bool labmate_pulse_pair_copy_locked(
    const LabMatePulsePairAudit* a, LabMatePulsePairObservation* o) {
    if(!a || !o) return false;
    LabMatePulsePairObservation s={0};
    s.pairs=a->pairs;
    s.edges=a->last_pair_edges;
    s.high_cycles=a->last_high_cycles;
    s.low_cycles=a->last_low_cycles;
    s.exhausted=a->exhausted;
    *o=s;
    return true;
}
