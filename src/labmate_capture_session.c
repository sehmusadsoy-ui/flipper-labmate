#include <furi.h>
#include <furi_hal.h>
#include <furi_hal_resources.h>
#include <storage/storage.h>
#include "labmate_internal.h"
#include "labmate_capture_session.h"
#include "labmate_measurements.h"
#include "labmate_monitor_gpio.h"
#include "labmate_frequency_capture.h"
#include "labmate_frequency_tim2.h"
#include "labmate_event_counter.h"
#include "labmate_button_capture.h"
#include "labmate_pulse_capture.h"
#include "labmate_capture_core.h"
#include "labmate_resource_policy.h"
#include "labmate_generator.h"
#include "labmate_logger_storage.h"
#include "labmate_scope_bridge.h"
#include "labmate_scope_exit_guard.h"

/* Pulse Analyzer uses GPIO edge interrupts, not polling.
 * STM32 EXTI lines are shared across GPIO ports, and the firmware already
 * uses EXTI3 for the OK button and EXTI6 for the DOWN button.
 * Therefore PC3/PB3 (line 3) and PA6 (line 6) MUST NOT be armed as IRQ
 * sources by this app. PA7 is also reserved for the signal generator.
 * GPIO Monitor retains all eight pins because it uses polling.
 *
 * Valid Pulse Analyzer input pins: PC0, PC1, PB2, PA4.
 */
static const uint8_t pulse_gpio_indices[] = {0U, 1U, 3U, 5U};
#define PULSE_GPIO_COUNT (sizeof(pulse_gpio_indices) / sizeof(pulse_gpio_indices[0]))

static uint8_t pulse_gpio_next_index(uint8_t current, int8_t direction) {
    size_t i = 0;
    for(; i < PULSE_GPIO_COUNT; i++) {
        if(pulse_gpio_indices[i] == current) break;
    }
    /* A previous tool may have selected a pin unavailable for IRQ capture. */
    if(i == PULSE_GPIO_COUNT) return 1U; /* PC1 */
    if(direction > 0) {
        i = (i + 1U) % PULSE_GPIO_COUNT;
    } else {
        i = (i + PULSE_GPIO_COUNT - 1U) % PULSE_GPIO_COUNT;
    }
    return pulse_gpio_indices[i];
}

/* Shared capture teardown. Each stop checks the existing active flags.
 * Detach capture IRQs and stop TIM2 before changing app->gpio_index.
 * Independent TIM1/PA7 background PWM is deliberately untouched.
 * Start paths and ISR timing remain unchanged in this first stage.
 */
void labmate_capture_stop_all(LabMateApp* app) {
    /* Stop the independent Scope-owned PC1 callback before old tool state
     * can clear capture_owner or overwrite its IRQ/EXTI configuration. */
    if(!labmate_scope_native_stop_confirmed(
           &app->scope_native, app->capture_owner)) {
        if(!labmate_scope_bridge_stop(app)) {
            app->capture_release_fault = true;
            app->capture_blocked = true;
        }
    }
    labmate_frequency_high_stop(app);
    labmate_frequency_low_stop(app);
    labmate_pulse_capture_stop(app);
    labmate_event_counter_stop(app);
    labmate_button_capture_stop(app);
    /* A failed/stale stop must not advertise a free capture owner. */
    if(!app->counter_active && !app->button_active &&
       labmate_scope_native_stop_confirmed(
           &app->scope_native, app->capture_owner) &&
       labmate_capture_all_stopped(
           app->frequency_irq_active, app->frequency_hw_active,
           app->pulse_irq_active)) {
        app->capture_owner = LabMateCaptureNone;
        app->capture_pin_index = GPIO_COUNT;
        /* Never erase an unresolved lease failure during generic STOP. */
        app->capture_blocked = app->capture_release_fault;
    } else {
        app->capture_blocked = true;
    }
}

/* Measurement state resets now live in labmate_measurements.c. */

void labmate_gpio_activate(LabMateApp* app) {
    labmate_monitor_gpio_activate(app);
    measurement_reset(app);
}

void labmate_gpio_change(
    LabMateApp* app,
    int8_t direction) {

    /*
     * Frequency Meter has two stable measurement modes:
     *
     * LEFT  -> PC1 / low-frequency period measurement
     * RIGHT -> PB3 / TIM2 hardware edge counter
     */
    if(app->screen == LabMateScreenFrequency) {
        uint8_t target_index =
            (direction > 0) ? 4U : 1U; /* PB3 : PC1 */

        if(app->gpio_index == target_index) {
            return;
        }

        labmate_capture_stop_all(app);

        labmate_monitor_gpio_release(app, app->gpio_index);

        app->gpio_index = target_index;
        app->preferred_frequency_pin = target_index;
        app->hold = false;

        frequency_stats_reset(app);
        measurement_reset(app);

        if(app->gpio_index == 4U) {
            labmate_frequency_high_start(app);
        } else {
            labmate_frequency_low_start(app);
        }

        return;
    }

    if(app->screen == LabMateScreenPulse) {
        const uint8_t next_index = pulse_gpio_next_index(app->gpio_index, direction);
        if(next_index == app->gpio_index) return;
        /* Detach the old EXTI callback before changing pin or IRQ state. */
        labmate_capture_stop_all(app);
        labmate_monitor_gpio_release(app, app->gpio_index);
        app->gpio_index = next_index;
        app->preferred_pulse_pin = next_index;
        app->hold = false;
        app->pulse_stats_view = false;
        pulse_stats_reset(app);
        measurement_reset(app);
        labmate_pulse_capture_start(app);
        return;
    }

    labmate_monitor_gpio_release(app, app->gpio_index);

    /* Preserve the original eight-pin navigation except that PA7 is not
     * selectable while Signal Generator keeps its PWM output active.
     */
    app->gpio_index =
        labmate_monitor_next_pin(
            app->gpio_index, direction,
            app->generator_running || app->generator_blocked ||
                app->generator_release_fault);
    labmate_gpio_activate(app);
}

/* Sampling, filtering and stats moved into labmate_measurements.c. */

/* ---------- DATA LOGGER v1.5 ---------- */
/* The capture engine is unchanged; only processed snapshots are persisted.
 * File writes happen in the main thread AFTER releasing the GUI mutex.
 */
void labmate_logger_capture_stop(LabMateApp* app) {
    labmate_capture_stop_all(app);
    labmate_monitor_gpio_release(app, app->gpio_index);
}

void labmate_logger_capture_start(LabMateApp* app) {
    app->hold = false;
    app->gpio_index =
        (app->logger_source == LoggerFrequencyHigh) ? 4U : 1U;
    measurement_reset(app);

    if(app->logger_source == LoggerPulse) {
        pulse_stats_reset(app);
        labmate_pulse_capture_start(app);
    } else {
        frequency_stats_reset(app);
        if(app->logger_source == LoggerFrequencyHigh) {
            labmate_frequency_high_start(app);
        } else {
            labmate_frequency_low_start(app);
        }
    }
}

void labmate_logger_capture_change(LabMateApp* app, int8_t direction) {
    if(app->logger_recording) return;
    labmate_logger_capture_stop(app);
    if(direction > 0) {
        app->logger_source =
            (app->logger_source + 1U) % LoggerSourceCount;
    } else {
        app->logger_source =
            (app->logger_source + LoggerSourceCount - 1U) % LoggerSourceCount;
    }
    labmate_logger_capture_start(app);
}

/* Logger file lifecycle moved to labmate_logger_storage.c.
 * App core still controls capture and deferred sample writes.
 */

/* CSV row snapshot/formatting moved to labmate_logger_snapshot.c. */

/* History file I/O now lives in labmate_history.c.
 * Renderers remain in labmate_ui_screens.c; CSV file IDs and CSV
 * formatting remain in labmate_logger_codec.c.
 */

/* Threshold sampling bridge moved into labmate_alerts_bridge.c. */
