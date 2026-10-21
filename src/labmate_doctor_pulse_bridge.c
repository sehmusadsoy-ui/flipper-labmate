#include "labmate_doctor_pulse_bridge.h"
#include "labmate_doctor_pulse_policy.h"
#include "labmate_evidence_session.h"
#include "labmate_pulse_capture.h"
#include <furi_hal.h>
#include <limits.h>

/* Saturating rather than wrapping an unproven device-uptime millisecond
 * field. A stopped session at or beyond the schema bound is not accepted.
 */
static uint32_t pulse_now_ms(uint32_t tick, uint32_t hz) {
    if(!hz) return 0U;
    const uint64_t ms = ((uint64_t)tick * 1000U) / hz;
    return ms > UINT32_MAX ? 0U : (uint32_t)ms;
}

void labmate_doctor_pulse_abandon(LabMateApp* app) {
    if(!app) return;
    /* Pin/mode change explicitly discards old evidence; it NEVER certifies
     * native E11 release. The existing capture stop retains fault ownership.
     */
    if(app->doctor_pulse_session.state == LabMateEvidenceCapturing)
        app->doctor_pulse_session.state = LabMateEvidenceIdle;
    labmate_dashboard_store_init(&app->doctor_store);
}

void labmate_doctor_pulse_started(LabMateApp* app) {
    if(!app || app->screen != LabMateScreenPulse) return;
    labmate_dashboard_store_init(&app->doctor_store);
    if(!app->pulse_irq_active || app->capture_owner != LabMateCapturePulse ||
       app->capture_release_fault || app->capture_blocked) return;
    const uint32_t hz = furi_kernel_get_tick_frequency();
    const uint32_t now = furi_get_tick();
    const uint32_t clock = SystemCoreClock;
    const uint32_t ms = pulse_now_ms(now, hz);
    if(!hz || !clock || !ms ||
       (DWT->CTRL & DWT_CTRL_CYCCNTENA_Msk) == 0U) return;
    if(!labmate_evidence_session_begin(
           &app->doctor_pulse_session, LabMateSnapshotPulse,
           app->capture_pin_index, ms, clock, true)) return;
    app->doctor_pulse_start_tick = now;
    app->doctor_pulse_tick_hz = hz;
    app->doctor_pulse_seen_pairs = 0U;
    app->doctor_pulse_last_pair_poll_tick = 0U;
}

/* App-thread only: monitor freshly increased paired IRQ publication IDs
 * copied coherently by measurement_update(). No redraw-time inference.
 */
void labmate_doctor_pulse_observe_poll(LabMateApp* app) {
    if(!app || app->screen != LabMateScreenPulse || app->hold ||
       !app->pulse_irq_active || app->capture_owner != LabMateCapturePulse ||
       app->doctor_pulse_session.state != LabMateEvidenceCapturing) return;
    const LabMatePulsePairObservation* pair = &app->pulse_pair_last_observation;
    if(pair->exhausted || pair->pairs <= app->doctor_pulse_seen_pairs) return;
    app->doctor_pulse_seen_pairs = pair->pairs;
    app->doctor_pulse_last_pair_poll_tick = furi_get_tick();
}

void labmate_doctor_pulse_prepare_stop(LabMateApp* app) {
    if(!app || app->doctor_pulse_session.state != LabMateEvidenceCapturing ||
       !app->pulse_irq_active) return;
    LabMateDoctorPulseCandidate c = {0};
    /* App mutex is NOT an ISR lock. Pair, last-edge tick, native owner and
     * native active state must be captured in ONE IRQ-critical interval.
     */
    FURI_CRITICAL_ENTER();
    (void)labmate_pulse_pair_copy_locked(&app->pulse_pair_audit, &c.pair);
    c.last_edge_tick = app->pulse_irq_last_tick;
    c.irq_active = app->pulse_irq_active;
    c.native_owner_confirmed = app->capture_owner == LabMateCapturePulse;
    FURI_CRITICAL_EXIT();
    c.observed_pair_count = app->doctor_pulse_seen_pairs;
    c.last_pair_poll_tick = app->doctor_pulse_last_pair_poll_tick;
    c.start_tick = app->doctor_pulse_start_tick;
    c.start_tick_hz = app->doctor_pulse_tick_hz;
    c.start_clock_hz = app->doctor_pulse_session.evidence.timebase_hz;
    c.stop_tick = furi_get_tick();
    c.stop_tick_hz = furi_kernel_get_tick_frequency();
    c.stop_clock_hz = SystemCoreClock;
    c.timebase_enabled = (DWT->CTRL & DWT_CTRL_CYCCNTENA_Msk) != 0U;
    c.release_fault = app->capture_release_fault;
    /* Publication is NEVER derived from live UI frequency/HOLD numbers.
     * PulsePair's recorded epoch and edge count are genuine native audit.
     */
    if(!labmate_doctor_pulse_policy_accept(&c)) {
        if(!c.timebase_enabled || c.start_clock_hz != c.stop_clock_hz ||
           c.start_tick_hz != c.stop_tick_hz)
            app->doctor_pulse_session.evidence.clock_unsafe = true;
        return;
    }
    const uint32_t period = c.pair.high_cycles + c.pair.low_cycles;
    const uint64_t freq = ((uint64_t)c.start_clock_hz * 1000U +
                           period / 2U) / period;
    const uint16_t duty = (uint16_t)(((uint64_t)c.pair.high_cycles * 1000U +
                                      period / 2U) / period);
    (void)labmate_evidence_session_record(
        &app->doctor_pulse_session, c.pair.pairs, c.pair.edges, 0U,
        (uint32_t)freq, c.pair.high_cycles, c.pair.low_cycles, period, duty);
}

void labmate_doctor_pulse_finish_stop(LabMateApp* app) {
    if(!app || app->doctor_pulse_session.state != LabMateEvidenceCapturing) return;
    const bool released = !app->pulse_irq_active &&
        app->capture_owner == LabMateCaptureNone &&
        !labmate_pulse_lease_pending() &&
        !app->capture_release_fault && !app->capture_blocked;
    const uint32_t hz = furi_kernel_get_tick_frequency();
    const uint32_t now = furi_get_tick();
    if(hz != app->doctor_pulse_tick_hz)
        app->doctor_pulse_session.evidence.clock_unsafe = true;
    const uint32_t end_ms = pulse_now_ms(now, hz);
    LabMateSnapshotV1 snapshot;
    if(labmate_evidence_session_finish(
           &app->doctor_pulse_session, end_ms, released, &snapshot))
        (void)labmate_dashboard_store_ingest(&app->doctor_store, &snapshot);
}
