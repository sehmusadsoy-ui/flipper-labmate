#include "labmate_doctor_frequency_bridge.h"
#include "labmate_doctor_frequency_policy.h"
#include "labmate_frequency_capture.h"
#include "labmate_frequency_tim2.h"
#include "labmate_frequency_gate.h"
#include <furi_hal.h>
#include <stdint.h>
#include <limits.h>

static uint32_t frequency_ms(uint32_t tick, uint32_t hz) {
    if(!hz) return 0U;
    const uint64_t ms = (uint64_t)tick * 1000U / hz;
    return ms > UINT32_MAX ? 0U : (uint32_t)ms;
}

void labmate_doctor_frequency_abandon(LabMateApp* a) {
    if(!a) return;
    /* Abandon is never ownership release; existing STOP determines that.
     * Preserve last_generation so mode changes cannot replay prior results.
     */
    if(a->doctor_frequency_session.state == LabMateEvidenceCapturing)
        a->doctor_frequency_session.state = LabMateEvidenceIdle;
    a->doctor_frequency_last = (LabMateDoctorFrequencyCandidate){0};
    labmate_dashboard_store_clear_source(&a->doctor_store, LabMateSnapshotFrequency);
}

void labmate_doctor_frequency_started(LabMateApp* a) {
    if(!a || a->screen != LabMateScreenFrequency) return;
    labmate_dashboard_store_clear_source(&a->doctor_store, LabMateSnapshotFrequency);
    const bool low = a->frequency_irq_active &&
        a->capture_owner == LabMateCaptureFrequencyLow &&
        a->capture_pin_index == 1U &&
        labmate_frequency_low_lease_pending();
    const bool high = a->frequency_hw_active &&
        a->capture_owner == LabMateCaptureFrequencyHigh &&
        a->capture_pin_index == 4U && labmate_frequency_tim2_capture_valid();
    if((!low && !high) || a->capture_release_fault || a->capture_blocked) return;
    const uint32_t hz = furi_kernel_get_tick_frequency();
    const uint32_t tick = furi_get_tick();
    const uint32_t cpu_hz = SystemCoreClock;
    const uint32_t ms = frequency_ms(tick, hz);
    if(!hz || !cpu_hz || !ms ||
       (DWT->CTRL & DWT_CTRL_CYCCNTENA_Msk) == 0U) return;
    const uint8_t pin = low ? 1U : 4U;
    if(!labmate_evidence_session_begin(
           &a->doctor_frequency_session, LabMateSnapshotFrequency, pin,
           ms, cpu_hz, true)) return;
    a->doctor_frequency_last = (LabMateDoctorFrequencyCandidate){
        .path = low ? LabMateDoctorFrequencyLowPC1 : LabMateDoctorFrequencyHighPB3,
        .pin_index = pin,
        .start_tick = tick,
        .start_tick_hz = hz,
        .start_clock_hz = cpu_hz,
    };
    a->doctor_frequency_seen_count = 0U;
    a->doctor_frequency_poisoned = false;
}

static bool frequency_owned(const LabMateApp* a) {
    if(!a || a->screen != LabMateScreenFrequency || a->hold ||
       a->doctor_frequency_session.state != LabMateEvidenceCapturing ||
       a->doctor_frequency_poisoned || a->capture_release_fault ||
       a->capture_blocked ||
       (DWT->CTRL & DWT_CTRL_CYCCNTENA_Msk) == 0U ||
       furi_kernel_get_tick_frequency() != a->doctor_frequency_last.start_tick_hz ||
       SystemCoreClock != a->doctor_frequency_last.start_clock_hz)
        return false;
    return a->doctor_frequency_last.path == LabMateDoctorFrequencyLowPC1 ?
        (a->frequency_irq_active &&
         a->capture_owner == LabMateCaptureFrequencyLow &&
         a->capture_pin_index == 1U &&
         labmate_frequency_low_lease_pending()) :
        (a->frequency_hw_active &&
         a->capture_owner == LabMateCaptureFrequencyHigh &&
         a->capture_pin_index == 4U &&
         labmate_frequency_tim2_capture_valid());
}

/* App-thread LOW handler receives the SAME atomic IRQ mailbox observation
 * plus edge count and last-edge tick; it does not read live UI smoothing.
 */
void labmate_doctor_frequency_note_low(
    LabMateApp* a, const LabMateLowMailboxObservation* o,
    uint32_t edges, uint32_t last_edge_tick) {
    if(!a || !o || a->doctor_frequency_session.state != LabMateEvidenceCapturing ||
       a->doctor_frequency_last.path != LabMateDoctorFrequencyLowPC1) return;
    if(!frequency_owned(a) || o->exhausted || o->overwrites ||
       !o->has_period || !o->period_cycles || !o->publications ||
       o->publications <= a->doctor_frequency_seen_count ||
       edges < 2U || edges <= a->doctor_frequency_last.irq_or_timer_edge_count ||
       edges < o->publications ||
       !last_edge_tick) {
        a->doctor_frequency_poisoned = true;
        return;
    }
    const uint64_t scale =
        (uint64_t)a->doctor_frequency_last.start_clock_hz * 1000U +
        o->period_cycles / 2U;
    const uint64_t measured = scale / o->period_cycles;
    if(measured == 0U || measured > UINT32_MAX) {
        a->doctor_frequency_poisoned = true;
        return;
    }
    const uint32_t now = furi_get_tick();
    if(now <= a->doctor_frequency_last.start_tick ||
       now < last_edge_tick ||
       (uint64_t)(now - last_edge_tick) * 2U >
           a->doctor_frequency_last.start_tick_hz) {
        a->doctor_frequency_poisoned = true;
        return;
    }
    LabMateDoctorFrequencyCandidate candidate = a->doctor_frequency_last;
    candidate.owned_active = true;
    candidate.source_clock_running = true;
    candidate.stop_tick = now;
    candidate.stop_tick_hz = furi_kernel_get_tick_frequency();
    candidate.stop_clock_hz = SystemCoreClock;
    candidate.last_publication_tick = now;
    candidate.irq_or_timer_edge_count = edges;
    candidate.publication_count = o->publications;
    candidate.frequency_millihz = (uint32_t)measured;
    candidate.low_period_cycles = o->period_cycles;
    candidate.low_mailbox_overwrites = o->overwrites;
    candidate.low_mailbox_exhausted = o->exhausted;
    if(!labmate_doctor_frequency_policy_accept(&candidate) ||
       !labmate_evidence_session_record(
           &a->doctor_frequency_session, o->publications, edges, 0U,
           candidate.frequency_millihz, 0U, 0U, o->period_cycles, 0U)) {
        a->doctor_frequency_poisoned = true;
        return;
    }
    a->doctor_frequency_last = candidate;
    a->doctor_frequency_seen_count = o->publications;
}

/* Called EXACTLY at production's successful TIM2 gate publication branch;
 * each event has been accepted by labmate_high_gate_audit_record.
 */
void labmate_doctor_frequency_note_high(LabMateApp* a) {
    if(!a || a->doctor_frequency_session.state != LabMateEvidenceCapturing ||
       a->doctor_frequency_last.path != LabMateDoctorFrequencyHighPB3) return;
    if(!frequency_owned(a)) {
        a->doctor_frequency_poisoned = true;
        return;
    }
    const LabMateHighGateAudit* audit = &a->frequency_high_gate_audit;
    if(audit->exhausted || !audit->publications ||
       audit->publications <= a->doctor_frequency_seen_count ||
       audit->last_counter < 2U ||
       audit->last_counter <= a->doctor_frequency_last.irq_or_timer_edge_count) {
        a->doctor_frequency_poisoned = true;
        return;
    }
    const uint32_t now = furi_get_tick();
    LabMateDoctorFrequencyCandidate candidate = a->doctor_frequency_last;
    candidate.owned_active = true;
    candidate.source_clock_running = true;
    candidate.stop_tick = now;
    candidate.stop_tick_hz = furi_kernel_get_tick_frequency();
    candidate.stop_clock_hz = SystemCoreClock;
    candidate.last_publication_tick = now;
    candidate.irq_or_timer_edge_count = audit->last_counter;
    candidate.publication_count = audit->publications;
    candidate.frequency_millihz = audit->last_frequency_millihz;
    candidate.high_gate_edges = audit->last_gate_edges;
    candidate.high_gate_cycles = audit->last_gate_cycles;
    candidate.high_audit_exhausted = audit->exhausted;
    if(!labmate_doctor_frequency_policy_accept(&candidate) ||
       !labmate_evidence_session_record(
           &a->doctor_frequency_session, audit->publications,
           audit->last_counter, 0U, audit->last_frequency_millihz,
           0U, 0U, 0U, 0U)) {
        a->doctor_frequency_poisoned = true;
        return;
    }
    a->doctor_frequency_last = candidate;
    a->doctor_frequency_seen_count = audit->publications;
}

/* Called while the real IRQ/TIM2 owner is STILL active; final closure
 * compares current audits to the last admitted native publication. It never
 * calls STOP or releases a foreign lease. All unproven races fail closed.
 */
void labmate_doctor_frequency_prepare_stop(LabMateApp* a) {
    if(!a || a->doctor_frequency_session.state != LabMateEvidenceCapturing) return;
    LabMateDoctorFrequencyCandidate c = a->doctor_frequency_last;
    c.owned_active = frequency_owned(a);
    c.release_fault = a->capture_release_fault || a->capture_blocked ||
        a->doctor_frequency_poisoned;
    c.hold = a->hold;
    c.stop_tick = furi_get_tick();
    c.stop_tick_hz = furi_kernel_get_tick_frequency();
    c.stop_clock_hz = SystemCoreClock;
    c.source_clock_running =
        (DWT->CTRL & DWT_CTRL_CYCCNTENA_Msk) != 0U &&
        (c.path == LabMateDoctorFrequencyLowPC1 ||
         labmate_frequency_tim2_capture_valid());

    if(c.path == LabMateDoctorFrequencyLowPC1) {
        uint32_t pubs = 0U, overwrites = 0U, irq_edges = 0U;
        bool exhausted = false;
        FURI_CRITICAL_ENTER();
        pubs = a->frequency_low_mailbox_audit.publications;
        overwrites = a->frequency_low_mailbox_audit.overwrites;
        exhausted = a->frequency_low_mailbox_audit.exhausted;
        irq_edges = a->frequency_irq_edges;
        FURI_CRITICAL_EXIT();
        if(overwrites || exhausted || pubs != a->doctor_frequency_seen_count ||
           irq_edges < c.irq_or_timer_edge_count)
            c.release_fault = true;
        c.low_mailbox_overwrites = overwrites;
        c.low_mailbox_exhausted = exhausted;
    } else {
        if(a->frequency_high_gate_audit.exhausted ||
           a->frequency_high_gate_audit.publications !=
               a->doctor_frequency_seen_count ||
           a->frequency_high_gate_audit.last_counter !=
               c.irq_or_timer_edge_count)
            c.release_fault = true;
    }
    if(!labmate_doctor_frequency_policy_accept(&c) ||
       a->doctor_frequency_session.evidence.completed_sample_count == 0U ||
       a->doctor_frequency_session.evidence.completed_sample_count !=
           a->doctor_frequency_seen_count ||
       a->doctor_frequency_session.evidence.observed_edge_count !=
           c.irq_or_timer_edge_count) {
        a->doctor_frequency_session.sample_fault = true;
    }
    if(c.start_clock_hz != c.stop_clock_hz ||
       c.start_tick_hz != c.stop_tick_hz || !c.source_clock_running)
        a->doctor_frequency_session.evidence.clock_unsafe = true;
}

void labmate_doctor_frequency_finish_stop(LabMateApp* a) {
    if(!a || a->doctor_frequency_session.state != LabMateEvidenceCapturing) return;
    const bool released = !a->frequency_irq_active && !a->frequency_hw_active &&
        a->capture_owner == LabMateCaptureNone &&
        !labmate_frequency_low_lease_pending() &&
        !labmate_frequency_tim2_lease_pending() &&
        !a->capture_release_fault && !a->capture_blocked;
    const uint32_t hz = furi_kernel_get_tick_frequency();
    if(hz != a->doctor_frequency_last.start_tick_hz)
        a->doctor_frequency_session.evidence.clock_unsafe = true;
    LabMateSnapshotV1 result;
    if(labmate_evidence_session_finish(
           &a->doctor_frequency_session, frequency_ms(furi_get_tick(), hz),
           released, &result))
        if(labmate_dashboard_store_ingest(&a->doctor_store, &result))
            (void)labmate_signal_stats_record(&a->signal_stats, &result);
}
