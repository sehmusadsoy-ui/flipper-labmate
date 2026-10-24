#include "labmate_doctor_frequency_policy.h"
#include "labmate_frequency_gate.h"
#include <stdint.h>

bool labmate_doctor_frequency_policy_accept(const LabMateDoctorFrequencyCandidate* c) {
    if(!c || (c->path != LabMateDoctorFrequencyLowPC1 &&
              c->path != LabMateDoctorFrequencyHighPB3) ||
       (c->path == LabMateDoctorFrequencyLowPC1 && c->pin_index != 1U) ||
       (c->path == LabMateDoctorFrequencyHighPB3 && c->pin_index != 4U) ||
       !c->owned_active || !c->source_clock_running || c->release_fault || c->hold ||
       !c->start_tick_hz || c->start_tick_hz != c->stop_tick_hz ||
       !c->start_clock_hz || c->start_clock_hz != c->stop_clock_hz ||
       c->stop_tick <= c->start_tick ||
       c->last_publication_tick < c->start_tick ||
       c->last_publication_tick > c->stop_tick ||
       c->irq_or_timer_edge_count < 2U || !c->publication_count ||
       !c->frequency_millihz) return false;

    const uint64_t duration = (uint64_t)c->stop_tick - c->start_tick;
    const uint64_t age = (uint64_t)c->stop_tick - c->last_publication_tick;
    if(duration * 1000U > (uint64_t)c->start_tick_hz * 300000U ||
       age * 2U > (uint64_t)c->start_tick_hz) return false;

    uint32_t checked = 0U;
    if(c->path == LabMateDoctorFrequencyLowPC1) {
        if(c->low_mailbox_overwrites || c->low_mailbox_exhausted ||
           c->high_gate_edges || c->high_gate_cycles || c->high_audit_exhausted ||
           !c->low_period_cycles || c->low_period_cycles >= UINT32_C(0x80000000) ||
           ((uint64_t)c->start_clock_hz * 1000U + c->low_period_cycles / 2U) /
                   c->low_period_cycles > UINT32_MAX ||
           !labmate_low_period_to_millihz(c->low_period_cycles,
                                         c->start_clock_hz, &checked)) return false;
    } else {
        if(c->low_period_cycles || c->low_mailbox_overwrites ||
           c->low_mailbox_exhausted || c->high_audit_exhausted ||
           c->high_gate_edges < LABMATE_HIGH_GATE_MIN_EDGES ||
           c->high_gate_edges > c->irq_or_timer_edge_count ||
           c->high_gate_cycles >= UINT32_C(0x80000000) ||
           labmate_high_gate_evaluate(c->high_gate_edges, c->high_gate_cycles,
                                     c->start_clock_hz, &checked) !=
               LabMateHighGatePublish) return false;
    }
    return checked == c->frequency_millihz;
}
