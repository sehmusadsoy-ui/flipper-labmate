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
void labmate_input_button(LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {

                if(event.key == InputKeyOk) {
                    if(app->button_active) {
                        labmate_button_capture_stop(app);
                    } else {
                        labmate_button_capture_start(app);
                    }
                } else if(event.key == InputKeyUp) {
                    /* Preserve measurements during RUN; clear them while stopped. */
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
                    labmate_gpio_change(app, -1);

                } else if(
                    event.key == InputKeyRight) {
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
                            app->hold = false;
                        } else {
                            /* Freeze displayed values and stop IRQ load. */
                            labmate_pulse_capture_stop(app);
                            app->hold = true;
                        }
                    } else {
                        app->hold = !app->hold;
                        if(!app->hold) {
                            app->gpio_state = labmate_monitor_gpio_read(app->gpio_index);
                            app->gpio_previous_state = app->gpio_state;
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
                    labmate_capture_stop_all(app);
                    labmate_monitor_gpio_release(app, app->gpio_index);

                    app->hold = false;
                    app->screen =
                        LabMateScreenMenu;
                }

}

