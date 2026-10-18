#include <furi.h>
#include <furi_hal.h>
#include <gui/gui.h>
#include <input/input.h>
#include "labmate_view.h"
#include "labmate_ui_screens.h"
#include "labmate_scope_display.h"
#include "labmate_scope_pair_view.h"
#include "labmate_scope_reference_view.h"
#include "labmate_scope_exit_guard.h"

/* ---------- DRAWING (stateful screens) ---------- */

void labmate_view_render_callback(
    Canvas* canvas,
    void* ctx) {

    LabMateApp* app = ctx;

    furi_mutex_acquire(
        app->mutex,
        FuriWaitForever);

    canvas_clear(canvas);

    switch(app->screen) {
    case LabMateScreenMenu:
        draw_menu(canvas, app);
        break;

    case LabMateScreenGpio:
        draw_gpio(canvas, app);
        break;

    case LabMateScreenFrequency:
        draw_frequency(canvas, app);
        break;

    case LabMateScreenPulse:
        draw_pulse(canvas, app);
        break;

    case LabMateScreenGenerator:
        draw_generator(canvas, app);
        break;

    case LabMateScreenLogger:
        draw_logger(canvas, app);
        break;

    case LabMateScreenUart:
        draw_uart(canvas, app);
        break;

    case LabMateScreenOneWire:
        draw_onewire(canvas, app);
        break;

    case LabMateScreenI2c:
        draw_i2c(canvas, app);
        break;

    case LabMateScreenHistory:
        draw_history(canvas, app);
        break;

    case LabMateScreenHistoryDetail:
        draw_history_detail(canvas, app);
        break;

    case LabMateScreenAbout:
        draw_about(canvas, app);
        break;
    case LabMateScreenProfiles:
        draw_profiles(canvas, app);
        break;
    case LabMateScreenCounter:
        draw_counter(canvas, app);
        break;
    case LabMateScreenButton:
        draw_button(canvas, app);
        break;
    case LabMateScreenAlerts:
        draw_alerts(canvas, app);
        break;
    case LabMateScreenScope:
        if(app->scope_show_reference) {
            const bool lease_clear = !app->scope_native.active &&
                !app->scope_native.owner.handle &&
                app->capture_owner == LabMateCaptureNone;
            const bool same_generation = app->scope_capture_generation != 0U &&
                app->scope_last_generation == app->scope_capture_generation;
            const bool complete = lease_clear && same_generation &&
                app->scope_last_valid && !app->scope_clock_fault;
            const LabMateScopeMetrics* measured =
                complete ? &app->scope_last_metrics : NULL;
            LabMateScopeObservation observation = LabMateScopeObservationInvalid;
            if(app->scope_display.state == LabMateScopeDisplayBusy) {
                observation = LabMateScopeObservationBusy;
            } else if(lease_clear && same_generation && !app->scope_clock_fault &&
                      app->scope_display.state == LabMateScopeDisplayNoTrigger &&
                      app->scope_display.total_edges == 0U) {
                observation = LabMateScopeObservationNoSignalConfirmed;
            } else if(complete) {
                observation = LabMateScopeObservationComplete;
            }
            LabMateScopeReference reference = {0};
            (void)labmate_scope_reference_preset(
                app->scope_reference_preset, &reference);
            const LabMateScopeToleranceResult result =
                labmate_scope_tolerance_evaluate(&reference, measured, observation);
            (void)labmate_scope_reference_view_draw(
                canvas, app->scope_reference_preset, result, measured);
        } else if(app->scope_show_compare) {
            /* "RIGHT SAVE B" must never be advertised for A's same
             * capture run; the pair backend requires a fresh generation. */
            const bool fresh_candidate = app->scope_last_valid &&
                (!app->scope_pair.has_a ||
                 app->scope_last_generation > app->scope_pair.generation_a);
            (void)labmate_scope_pair_view_draw(
                canvas, &app->scope_pair, fresh_candidate);
        } else {
            (void)labmate_scope_display_draw(canvas, &app->scope_display);
        }
        break;
    }

    furi_mutex_release(
        app->mutex);
}

void labmate_view_input_callback(
    InputEvent* input_event,
    void* ctx) {

    FuriMessageQueue* queue =
        ctx;

    furi_message_queue_put(
        queue,
        input_event,
        0);
}

bool labmate_screen_uses_gpio(
    LabMateScreen screen) {

    return
        screen == LabMateScreenGpio ||
        screen == LabMateScreenFrequency ||
        screen == LabMateScreenPulse ||
        screen == LabMateScreenLogger;
}

void labmate_redraw_init(LabMateRedrawThrottle* state) {
    /* GUI refresh is 10 Hz normally, 5 Hz from 8 kHz upward.
     * Measurement remains interrupt-driven at every signal edge.
     */
    state->pulse_redraw_interval = furi_kernel_get_tick_frequency() / 10U;
    state->pulse_busy_redraw_interval = furi_kernel_get_tick_frequency() / 5U;
    if(state->pulse_redraw_interval == 0U) state->pulse_redraw_interval = 1U;
    if(state->pulse_busy_redraw_interval == 0U) state->pulse_busy_redraw_interval = 1U;
    state->pulse_fast_period_cycles = SystemCoreClock / 8000U;
    state->pulse_redraw_last_tick = furi_get_tick();

    /* Diagnostic v1.4: avoid unnecessary 100 Hz repaint of the main menu
     * while attached to the USB host. Keys still trigger an immediate redraw.
     * Pulse Analyzer retains its separately throttled redraw policy. */
    state->normal_redraw_interval = furi_kernel_get_tick_frequency() / 10U;
    if(state->normal_redraw_interval == 0U) state->normal_redraw_interval = 1U;
    state->normal_redraw_last_tick = furi_get_tick();

}

void labmate_redraw_maybe(LabMateRedrawThrottle* state, LabMateApp* app,
                          FuriStatus status, InputEvent event, ViewPort* viewport) {
        /* Under heavy IRQ load, use a calmer LCD refresh rate while
         * preserving immediate response to keys and all captured edges.
         */
        if(app->screen == LabMateScreenPulse ||
           (app->screen == LabMateScreenLogger && app->logger_source == LoggerPulse)) {
            uint32_t tick = furi_get_tick();
            bool key_press =
                (status == FuriStatusOk && event.type == InputTypePress);
            const uint32_t redraw_interval =
                (app->pulse_period_valid && state->pulse_fast_period_cycles > 0U &&
                 app->pulse_period_cycles <= state->pulse_fast_period_cycles)
                    ? state->pulse_busy_redraw_interval
                    : state->pulse_redraw_interval;
            if(key_press ||
               (uint32_t)(tick - state->pulse_redraw_last_tick) >= redraw_interval) {
                view_port_update(viewport);
                state->pulse_redraw_last_tick = tick;
            }
        } else {
            const uint32_t redraw_tick = furi_get_tick();
            if(status == FuriStatusOk ||
               (uint32_t)(redraw_tick - state->normal_redraw_last_tick) >= state->normal_redraw_interval) {
                view_port_update(viewport);
                state->normal_redraw_last_tick = redraw_tick;
            }
        }
}
