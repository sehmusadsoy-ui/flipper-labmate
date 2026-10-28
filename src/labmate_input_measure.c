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

#include "labmate_input.h"
#include "labmate_deferred.h"
#include "labmate_navigation.h"
#include "labmate_history.h"
#include "labmate_view.h"

#include "labmate_input_tools.h"
#include "labmate_doctor_pulse_bridge.h"
#include "labmate_doctor_frequency_bridge.h"
#include "labmate_capture_live.h"
void labmate_input_button(LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {
    UNUSED(work);

                if(event.key == InputKeyOk) {
                    if(app->button_active) {
                        labmate_button_capture_stop(app);
                    } else {
                        labmate_button_capture_start(app);
                    }
                } else if(event.key == InputKeyUp) {
                    /* RESET works only during STOP; RUN cannot erase counters. */
                    labmate_button_capture_reset(app);
                } else if(event.key == InputKeyLeft) {
                    labmate_button_capture_change_quiet(app, -1);
                } else if(event.key == InputKeyRight) {
                    labmate_button_capture_change_quiet(app, 1);
                } else if(event.key == InputKeyDown) {
                    /* Paging is display-only; never reset or re-arm EXTI. */
                    app->button_details_view = !app->button_details_view;
                } else if(event.key == InputKeyBack) {
                    labmate_capture_stop_all(app);
                    app->screen = LabMateScreenMenu;
                }

}

void labmate_input_counter(LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {
    UNUSED(work);

                if(event.key == InputKeyOk) {
                    if(app->counter_active) {
                        labmate_event_counter_stop(app);
                    } else {
                        labmate_event_counter_start(app);
                    }
                } else if(event.key == InputKeyUp) {
                    /* Preserve the previous result while RUN; reset only STOP. */
                    labmate_event_counter_reset(app);
                } else if(event.key == InputKeyBack) {
                    /* Never carry TIM2 counting into another tool. */
                    labmate_capture_stop_all(app);
                    app->screen = LabMateScreenMenu;
                }

}

void labmate_input_gpio(LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {
    UNUSED(work);


                if(app->screen == LabMateScreenFrequency &&
                   event.key == InputKeyUp) {
                    if(!app->hold) frequency_stats_reset(app);

                } else if(app->screen == LabMateScreenPulse &&
                          event.key == InputKeyUp) {
                    app->pulse_stats_view = !app->pulse_stats_view;

                } else if(app->screen == LabMateScreenPulse &&
                          event.key == InputKeyDown) {
                    if(!app->hold) pulse_stats_reset(app);

                } else if(event.key == InputKeyLeft) {
                    if(app->screen == LabMateScreenPulse)
                        labmate_doctor_pulse_abandon(app);
                    if(app->screen == LabMateScreenFrequency &&
                       app->gpio_index != 1U)
                        labmate_doctor_frequency_abandon(app);
                    labmate_gpio_change(app, -1);

                } else if(
                    event.key == InputKeyRight) {
                    if(app->screen == LabMateScreenPulse)
                        labmate_doctor_pulse_abandon(app);
                    if(app->screen == LabMateScreenFrequency &&
                       app->gpio_index != 4U)
                        labmate_doctor_frequency_abandon(app);
                    labmate_gpio_change(app, 1);

                } else if(
                    event.key == InputKeyOk) {

                    if(app->screen == LabMateScreenPulse) {
                        if(app->hold) {
                            /* Resume with a fresh IRQ and statistics window.
                             * Keep prior recorded extrema across HOLD/LIVE. */
                            pulse_stats_window_reset(app);
                            measurement_reset(app);
                            labmate_pulse_capture_start(app);
                            /* Failed lease/TRY-ADD must not advertise LIVE. */
                            app->hold = !labmate_pulse_ui_live(
                                app->pulse_irq_active,
                                app->capture_owner == LabMateCapturePulse,
                                app->capture_blocked, app->capture_release_fault);
                        } else {
                            /* Freeze displayed values and stop IRQ load. */
                            labmate_doctor_pulse_prepare_stop(app);
                            labmate_pulse_capture_stop(app);
                            labmate_doctor_pulse_finish_stop(app);
                            app->hold = true;
                        }
                    } else {
                        /* Frequency HOLD retains the native IRQ/TIM2 lease.
                         * It is NOT a STOP and can never certify a Doctor
                         * reading, including on subsequent HOLD resume.
                         */
                        if(app->screen == LabMateScreenFrequency)
                            labmate_doctor_frequency_abandon(app);
                        if(app->screen == LabMateScreenFrequency && app->hold &&
                           !labmate_frequency_ui_live(
                               app->gpio_index == 4U,
                               app->frequency_hw_active, app->frequency_irq_active,
                               app->capture_owner == (app->gpio_index == 4U ?
                                   LabMateCaptureFrequencyHigh : LabMateCaptureFrequencyLow),
                               app->capture_blocked, app->capture_release_fault)) {
                            /* A denied start remains retryable on OK. */
                            if(app->gpio_index == 4U)
                                labmate_frequency_high_start(app);
                            else
                                labmate_frequency_low_start(app);
                        }
                        if(app->screen == LabMateScreenFrequency) {
                            const bool live = labmate_frequency_ui_live(
                                app->gpio_index == 4U,
                                app->frequency_hw_active, app->frequency_irq_active,
                                app->capture_owner == (app->gpio_index == 4U ?
                                    LabMateCaptureFrequencyHigh : LabMateCaptureFrequencyLow),
                                app->capture_blocked, app->capture_release_fault);
                            app->hold = !live || !app->hold;
                        } else {
                            app->hold = !app->hold;
                        }
                        if(!app->hold) {
                            /* HOLD resume cannot treat an unowned GPIO
                             * as a valid electrical LOW sample. */
                            if(app->screen == LabMateScreenGpio) {
                                bool level = false;
                                if(labmate_monitor_gpio_read(
                                       app, app->gpio_index, &level)) {
                                    app->gpio_state = level;
                                    app->gpio_previous_state = level;
                                }
                            }
                            measurement_reset(app);
                            if(app->screen == LabMateScreenFrequency &&
                               app->frequency_hw_active) {
                                const uint32_t count = labmate_frequency_tim2_read();
                                const uint32_t cycle = DWT->CYCCNT;
                                app->frequency_hw_last_count = count;
                                app->frequency_hw_last_poll_count = count;
                                app->frequency_hw_last_cycle = cycle;
                                app->frequency_hw_last_poll_cycle = cycle;
                                app->frequency_hw_gate_started = false;
                            }
                        }
                    }

                } else if(
                    event.key == InputKeyBack) {

                    /* Release active capture before returning to Menu. */
                    if(app->screen == LabMateScreenPulse)
                        labmate_doctor_pulse_prepare_stop(app);
                    if(app->screen == LabMateScreenFrequency)
                        labmate_doctor_frequency_prepare_stop(app);
                    labmate_capture_stop_all(app);
                    if(app->screen == LabMateScreenPulse)
                        labmate_doctor_pulse_finish_stop(app);
                    if(app->screen == LabMateScreenFrequency)
                        labmate_doctor_frequency_finish_stop(app);
                    labmate_monitor_gpio_release(app, app->gpio_index);

                    app->hold = false;
                    app->screen =
                        LabMateScreenMenu;
                }

}

