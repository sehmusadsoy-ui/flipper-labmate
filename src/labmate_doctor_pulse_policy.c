#include "labmate_doctor_pulse_policy.h"
#include <stdint.h>
#include <limits.h>

bool labmate_doctor_pulse_policy_accept(const LabMateDoctorPulseCandidate* c) {
    if(!c || !c->native_owner_confirmed || !c->irq_active ||
       !c->timebase_enabled || c->release_fault ||
       !c->start_tick_hz || c->start_tick_hz != c->stop_tick_hz ||
       !c->start_clock_hz || c->start_clock_hz != c->stop_clock_hz ||
       c->stop_tick <= c->start_tick ||
       c->last_edge_tick < c->start_tick ||
       c->last_edge_tick > c->stop_tick ||
       c->last_pair_poll_tick < c->start_tick ||
       c->last_pair_poll_tick > c->stop_tick ||
       c->observed_pair_count != c->pair.pairs) return false;
    /* Reject ambiguous wrap and sessions > five minutes. Latest observed IRQ
     * edge must be within 500ms of STOP, not a retained HOLD/sample value.
     */
    const uint64_t duration = (uint64_t)c->stop_tick - c->start_tick;
    const uint64_t age = (uint64_t)c->stop_tick - c->last_edge_tick;
    const uint64_t pair_age = (uint64_t)c->stop_tick - c->last_pair_poll_tick;
    if(duration * 1000U > (uint64_t)c->start_tick_hz * 300000U ||
       age * 2U > (uint64_t)c->start_tick_hz ||
       pair_age * 2U > (uint64_t)c->start_tick_hz) return false;
    const LabMatePulsePairObservation* p = &c->pair;
    if(p->exhausted || !p->pairs || p->edges < 3U ||
       !p->high_cycles || !p->low_cycles ||
       (uint64_t)p->high_cycles + p->low_cycles > UINT32_MAX) return false;
    const uint32_t period = p->high_cycles + p->low_cycles;
    const uint64_t freq_mhz = ((uint64_t)c->start_clock_hz * 1000U +
                               period / 2U) / period;
    if(!freq_mhz || freq_mhz > UINT32_MAX) return false;
    return true;
}
