#include <furi.h>
#include <furi_hal.h>
#include <gui/gui.h>
#include <input/input.h>
#include <stdlib.h>
#include <string.h>
#include "labmate_internal.h"
#include "labmate_generator.h"
#include "labmate_view.h"
#include "labmate_capture_session.h"
#include "labmate_input.h"
#include "labmate_deferred.h"
#include "labmate_event_counter.h"
#include "labmate_button_capture.h"
#include "labmate_measurements.h"
#include "labmate_alerts_bridge.h"
#include "labmate_history.h"
#include "labmate_logger_storage.h"
#include "labmate_uart.h"
#include "labmate_monitor_gpio.h"
#include "labmate_scope_bridge.h"
#include "labmate_scope_exit_guard.h"
#include "labmate_doctor_pulse_bridge.h"
#include "labmate_ui_motion.h"
#include "labmate_ui_prefs_storage.h"

/* App coordinator: lifecycle, sampling, dispatch and teardown only. */
int32_t labmate_app(void* p) {
    UNUSED(p);

    LabMateApp* app =
        malloc(sizeof(LabMateApp));

    if(!app) {
        return -1;
    }

    memset(
        app,
        0,
        sizeof(LabMateApp));
    /* Scope's 256-edge buffer belongs to heap-allocated app state,
     * not the Flipper's 4 KiB application call stack. */
    if(!labmate_scope_bridge_init(app)) {
        free(app);
        return -1;
    }

    app->running = true;
    app->hold = false;
    app->selected = 0;
    app->menu_group = LabMateGroupMeasure;
    app->menu_in_group = false;
    app->gpio_index = 1; /* PC1 */
    app->preferred_frequency_pin = 4U; /* HIGH PB3 by default */
    app->preferred_pulse_pin = 1U; /* Pulse PC1 by default */
    app->profile_active_copy = LABMATE_PROFILE_COPY_NONE;
    app->profile_io = LabMateProfileIoEmpty;
    labmate_profile_store_init(&app->profiles);
    labmate_doctor_panel_init(&app->doctor_panel);
    labmate_dashboard_store_init(&app->doctor_store);
    labmate_signal_stats_init(&app->signal_stats);
    labmate_evidence_session_init(&app->doctor_pulse_session);
    labmate_evidence_session_init(&app->doctor_frequency_session);
    app->generator_freq_index = 0; /* 1 Hz */
    app->generator_duty_percent = LABMATE_PWM_DEFAULT_DUTY;
    app->generator_custom_hz = 1234U; /* independently editable 1 Hz steps */
    app->button_quiet_index = 1U; /* 10 ms quiet-time default */
    app->button_quiet_ms = 10U;
    labmate_button_capture_reset(app);
    labmate_threshold_init(&app->threshold);
    labmate_uart_reset(&app->uart);
    labmate_onewire_hw_init(&app->thermometer);
    app->comm_owner = LabMateCommNone;
    app->i2c = labmate_i2c_runtime_alloc();
    if(!app->i2c) {
        free(app);
        return -1;
    }
    app->screen = LabMateScreenMenu;
    app->capture_owner = LabMateCaptureNone;
    app->capture_pin_index = GPIO_COUNT;
    /* Read only before GUI creation: no startup SD writes or lock contention. */
    app->ui_prefs_io = labmate_ui_prefs_sd_load(
        &app->ui_prefs, &app->ui_prefs_active_copy);
    labmate_ui_motion_init(app);

    app->mutex =
        furi_mutex_alloc(
            FuriMutexTypeNormal);

    if(!app->mutex) {
        labmate_i2c_runtime_free(app->i2c);
        free(app);
        return -1;
    }

    FuriMessageQueue* queue =
        furi_message_queue_alloc(
            16,
            sizeof(InputEvent));

    if(!queue) {
        labmate_i2c_runtime_free(app->i2c);
        furi_mutex_free(app->mutex);
        free(app);
        return -1;
    }

    ViewPort* viewport =
        view_port_alloc();

    if(!viewport) {
        labmate_i2c_runtime_free(app->i2c);
        furi_message_queue_free(queue);
        furi_mutex_free(app->mutex);
        free(app);
        return -1;
    }

    view_port_draw_callback_set(
        viewport,
        labmate_view_render_callback,
        app);

    view_port_input_callback_set(
        viewport,
        labmate_view_input_callback,
        queue);

    Gui* gui =
        furi_record_open(
            RECORD_GUI);

    gui_add_view_port(
        gui,
        viewport,
        GuiLayerFullscreen);

    InputEvent event = {0};

    LabMateRedrawThrottle redraw;
    labmate_redraw_init(&redraw);

    while(app->running) {
        LabMateDeferredWork work = {0};
        work.proposed_copy = LABMATE_PROFILE_COPY_NONE;
        work.proposed_ui_prefs_copy = LABMATE_UI_PREFS_COPY_NONE;
        FuriStatus status =
            furi_message_queue_get(
                queue,
                &event,
                10);

        furi_mutex_acquire(
            app->mutex,
            FuriWaitForever);

        if(labmate_screen_uses_gpio(
               app->screen)) {
            measurement_update(app);
            if(app->screen == LabMateScreenPulse)
                labmate_doctor_pulse_observe_poll(app);
        }
        if(app->screen == LabMateScreenCounter) {
            labmate_event_counter_poll(app);
        }
        if(app->screen == LabMateScreenButton) {
            labmate_button_capture_poll(app);
        }
        if(app->screen == LabMateScreenScope) {
            labmate_scope_bridge_poll(app);
        }
        threshold_update_from_measurement(app);
        if(app->screen == LabMateScreenUart) labmate_uart_poll(&app->uart);
        if(app->screen == LabMateScreenOneWire) labmate_onewire_hw_poll(&app->thermometer);
        if(app->i2c) labmate_i2c_runtime_poll(app->i2c);

        labmate_input_dispatch(app, status, event, &work);
        labmate_ui_motion_step(app);
        labmate_deferred_prepare(app, &work);
        furi_mutex_release(app->mutex);

        labmate_deferred_execute(app, &work, viewport);
        labmate_redraw_maybe(&redraw, app, status, event, viewport);
    }

    /* Defensive cleanup even if a future route exits while UART RUN. */
    labmate_uart_stop(&app->uart);
    labmate_onewire_hw_stop(&app->thermometer);
    labmate_i2c_runtime_free(app->i2c);
    app->i2c = NULL;

    if(app->generator_running) {
        labmate_generator_stop(app);
    }

    if(app->logger_recording || app->logger_file || app->logger_storage) {
        labmate_logger_storage_stop(app);
    }
    labmate_history_close(app);

    /* Teardown must not depend on which screen was visible on exit.
     * A stale capture owner must never survive a future menu route.
     * Snapshot the armed pin before stop_all resets capture_pin_index. */
    const uint8_t captured_gpio_index = app->capture_pin_index;
    labmate_capture_stop_all(app);
    if(captured_gpio_index < GPIO_COUNT) {
        labmate_monitor_gpio_release(app, captured_gpio_index);
    }
    /* GPIO Monitor has no capture owner; release its selected input too.
     * Avoid releasing the same GPIO twice for capture screens. */
    if(labmate_screen_uses_gpio(app->screen) &&
       app->gpio_index != captured_gpio_index) {
        labmate_monitor_gpio_release(app, app->gpio_index);
    }

    gui_remove_view_port(
        gui,
        viewport);

    view_port_free(
        viewport);

    furi_record_close(
        RECORD_GUI);

    furi_message_queue_free(
        queue);

    furi_mutex_free(
        app->mutex);

    /* A native IRQ callback points to app-owned state AND executable FAP
     * code. If owned teardown is uncertain, returning from labmate_app()
     * risks unloading the callback's code even if the heap is leaked.
     * Quiesce our own handler flag first, then trigger Furi's controlled
     * crash/reboot path rather than return with a potentially live IRQ.
     * NEVER release another owner's callback or modify foreign GPIO here.
     * This emergency path requires a separate native fault-injection test;
     * ordinary successful STOP/BACK still exits normally. */
    if(!labmate_scope_exit_storage_safe(&app->scope_native)) {
        FURI_CRITICAL_ENTER();
        app->scope_native.irq_enabled = false;
        FURI_CRITICAL_EXIT();
        FURI_LOG_E("LabMate", "Scope IRQ cleanup uncertain; reboot required");
        furi_crash("LabMate Scope IRQ cleanup fault");
    }

    free(app);

    return 0;
}
