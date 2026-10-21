#include "labmate_event_counter.h"

#include "labmate_capture_core.h"
#include "labmate_counter_math.h"
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
