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

    /* Reset the physical timer and its software baseline before enabling. */
    labmate_frequency_tim2_configure();
    app->counter_last_hw = 0U;
    app->counter_total = 0U;
    app->counter_start_tick = furi_get_tick();
    app->counter_elapsed_seconds = 0U;
    app->counter_active = true;
    app->capture_pin_index = app->gpio_index;
    app->capture_owner = LabMateCaptureCounter;
    labmate_frequency_tim2_enable();
}

void labmate_event_counter_poll(LabMateApp* app) {
    if(!app->counter_active || app->capture_owner != LabMateCaptureCounter) return;
    const uint32_t current = labmate_frequency_tim2_read();
    app->counter_total =
        labmate_counter_accumulate(app->counter_total, app->counter_last_hw, current);
    app->counter_last_hw = current;
    const uint32_t tick_frequency = furi_kernel_get_tick_frequency();
    if(tick_frequency > 0U) {
        app->counter_elapsed_seconds =
            (uint32_t)((furi_get_tick() - app->counter_start_tick) / tick_frequency);
    }
}

void labmate_event_counter_stop(LabMateApp* app) {
    if(!app->counter_active) return;
    /* Stop TIM2 before consuming its last snapshot, so no edges are missed
     * between the last read and hardware release.
     */
    labmate_frequency_tim2_disable();
    if(app->capture_owner == LabMateCaptureCounter) {
        labmate_event_counter_poll(app);
    }
    labmate_frequency_tim2_shutdown();
    app->counter_active = false;
    if(app->capture_owner == LabMateCaptureCounter) {
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
    app->counter_elapsed_seconds = 0U;
}
