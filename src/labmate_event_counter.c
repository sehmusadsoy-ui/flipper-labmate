#include "labmate_event_counter.h"

#include "labmate_capture_core.h"
#include "labmate_counter_math.h"
#include "labmate_dashboard_store.h"
#include "labmate_frequency_tim2.h"
#include "labmate_resource_policy.h"
#include <furi.h>

void labmate_event_counter_start(LabMateApp* app) {
    if(app->counter_active) return;
    /* Do not touch PB3/TIM2 if Frequency or Pulse owns a capture engine. */
    if(!labmate_capture_can_start(app, LabMateCaptureCounter)) return;

    /* Each RUN starts a fresh hardware capture but resumes the same software
     * count/time until UP RESET or a new Counter tool entry. */
    if(!labmate_frequency_tim2_configure()) {
        app->capture_blocked = true;
        /* BUSY if a legacy native timer is already active; ERR if the
         * fresh lease could not be released and must remain reserved.
         */
        if(labmate_frequency_tim2_lease_pending()) app->capture_release_fault = true;
        return;
    }
    app->counter_last_hw = 0U;
    app->counter_start_tick = furi_get_tick();
    app->counter_active = true;
    app->capture_pin_index = app->gpio_index;
    app->capture_owner = LabMateCaptureCounter;
    labmate_frequency_tim2_enable();
    if(app->counter_run_generation != UINT32_MAX)
        ++app->counter_run_generation;
    else app->counter_run_generation = 0U; /* no ambiguous reused generation */
    app->counter_run_tick_hz = furi_kernel_get_tick_frequency();
    app->counter_run_start_total = app->counter_total;
    labmate_dashboard_store_clear_source(
        &app->doctor_store, LabMateSnapshotCounter);
}

void labmate_event_counter_poll(LabMateApp* app) {
    if(!app->counter_active || app->capture_owner != LabMateCaptureCounter) return;
    if(!labmate_frequency_tim2_capture_valid()) {
        /* The timer may have been seized or its clock disabled by a
         * legacy owner. Preserve the last real count, never accumulate
         * a guarded zero as a wrapped 32-bit counter.
         */
        app->capture_release_fault = true;
        app->capture_blocked = true;
        return;
    }
    const uint32_t current = labmate_frequency_tim2_read();
    app->counter_total =
        labmate_counter_accumulate(app->counter_total, app->counter_last_hw, current);
    app->counter_last_hw = current;
    const uint32_t tick_frequency = furi_kernel_get_tick_frequency();
    if(tick_frequency > 0U) {
        const uint32_t active_ticks = (uint32_t)(furi_get_tick() - app->counter_start_tick);
        const uint64_t total_ticks =
            labmate_counter_add_ticks(app->counter_elapsed_ticks, active_ticks);
        app->counter_elapsed_seconds =
            labmate_counter_elapsed_seconds(total_ticks, tick_frequency);
    }
}

void labmate_event_counter_stop(LabMateApp* app) {
    if(!app->counter_active) return;
    /* Stop TIM2 before consuming its last snapshot, so no edges are missed
     * between the last read and hardware release.
     */
    const bool healthy = labmate_frequency_tim2_capture_valid();
    if(healthy) labmate_frequency_tim2_disable();
    else {
        app->capture_release_fault = true;
        app->capture_blocked = true;
    }
    if(healthy && app->capture_owner == LabMateCaptureCounter) {
        labmate_event_counter_poll(app);
        app->counter_elapsed_ticks = labmate_counter_add_ticks(
            app->counter_elapsed_ticks, (uint32_t)(furi_get_tick() - app->counter_start_tick));
        const uint32_t hz = furi_kernel_get_tick_frequency();
        if(hz != 0U) {
            app->counter_elapsed_seconds =
                labmate_counter_elapsed_seconds(app->counter_elapsed_ticks, hz);
        }
    }
    labmate_frequency_tim2_shutdown();
    const bool lease_pending = labmate_frequency_tim2_lease_pending();
    if(lease_pending) {
        app->capture_release_fault = true;
        app->capture_blocked = true;
    }
    app->counter_active = false;
    /* Preserve PB3 owner until genuine lease return (and healthy stop). */
    if(!lease_pending && healthy && !app->capture_release_fault &&
       app->capture_owner == LabMateCaptureCounter) {
        app->capture_owner =
            labmate_capture_owner_after_stop(app->capture_owner, LabMateCaptureCounter);
        app->capture_pin_index = GPIO_COUNT;

        /* Real hardware stopped and both native lease/owner released.
         * A 64-bit cumulative software count is not a single RUN: emit
         * only the delta since this native START; never infer zero-signal.
         */
        const uint32_t end_tick = furi_get_tick();
        const uint32_t hz = furi_kernel_get_tick_frequency();
        if(hz && hz == app->counter_run_tick_hz &&
           end_tick > app->counter_start_tick &&
           app->counter_run_generation != 0U &&
           app->counter_total >= app->counter_run_start_total) {
            const uint64_t delta = app->counter_total - app->counter_run_start_total;
            const uint64_t start_ms =
                ((uint64_t)app->counter_start_tick * 1000U) / hz;
            const uint64_t end_ms = ((uint64_t)end_tick * 1000U) / hz;
            if(start_ms && end_ms <= UINT32_MAX && end_ms > start_ms) {
                LabMateSnapshotV1 s = {0};
                s.schema_version = LABMATE_SNAPSHOT_VERSION;
                s.source = LabMateSnapshotCounter;
                s.pin_index = 4U; /* verified PB3 TIM2 input */
                s.capture_generation = app->counter_run_generation;
                s.observation_start_ms = (uint32_t)start_ms;
                s.observation_end_ms = (uint32_t)end_ms;
                s.timebase_hz = hz;
                s.ownership_released = true;
                if(delta == 0U) s.quality = LabMateSnapshotInsufficient;
                else if(delta > UINT32_MAX) s.quality = LabMateSnapshotOverflow;
                else {
                    s.quality = LabMateSnapshotValid;
                    s.valid_sample_count = (uint32_t)delta;
                    s.observed_edge_count = (uint32_t)delta;
                }
                (void)labmate_dashboard_store_ingest(&app->doctor_store, &s);
            }
        }
    }
}

void labmate_event_counter_reset(LabMateApp* app) {
    /* Reset is only permitted once PB3 has been detached. */
    if(app->counter_active) return;
    app->counter_total = 0U;
    app->counter_last_hw = 0U;
    app->counter_start_tick = 0U;
    app->counter_elapsed_ticks = 0U;
    app->counter_elapsed_seconds = 0U;
}
