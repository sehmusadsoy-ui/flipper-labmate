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
void labmate_input_alerts(LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {
    UNUSED(work);

                if(event.key == InputKeyLeft) {
                    labmate_threshold_change_source(&app->threshold, -1);
                } else if(event.key == InputKeyRight) {
                    labmate_threshold_change_source(&app->threshold, 1);
                } else if(event.key == InputKeyUp) {
                    labmate_threshold_change_limit(&app->threshold, 1);
                } else if(event.key == InputKeyDown) {
                    if(app->threshold.armed) {
                        labmate_threshold_acknowledge(&app->threshold);
                    } else {
                        labmate_threshold_change_limit(&app->threshold, -1);
                    }
                } else if(event.key == InputKeyOk) {
                    labmate_threshold_toggle(&app->threshold);
                } else if(event.key == InputKeyBack) {
                    /* Alerts do not claim GPIO; keep config across navigation. */
                    app->screen = LabMateScreenMenu;
                }

}

void labmate_input_generator(LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {
    UNUSED(work);

                /* A menu-OK release is not a request to run the generator. */
                if(app->generator_skip_entry_ok && event.key == InputKeyOk) {
                    app->generator_skip_entry_ok = false;
                } else if(app->generator_editing) {
                    if(event.type == InputTypeShort) {
                        if(event.key == InputKeyLeft) {
                            labmate_generator_custom_adjust(app, -1);
                        } else if(event.key == InputKeyRight) {
                            labmate_generator_custom_adjust(app, 1);
                        } else if(event.key == InputKeyUp) {
                            labmate_generator_custom_step(app, 1);
                        } else if(event.key == InputKeyDown) {
                            labmate_generator_custom_step(app, -1);
                        } else if(event.key == InputKeyOk) {
                            labmate_generator_finish_custom_edit(app, true);
                        } else if(event.key == InputKeyBack) {
                            labmate_generator_finish_custom_edit(app, false);
                        }
                    }
                } else if(event.type == InputTypeLong &&
                          event.key == InputKeyOk) {
                    /* Never reconfigure a live PWM output from an unfinished edit. */
                    (void)labmate_generator_begin_custom_edit(app);
                } else if(event.type == InputTypeShort) {
                    if(event.key == InputKeyLeft) {
                        labmate_generator_change_frequency(app, -1);
                    } else if(event.key == InputKeyRight) {
                        labmate_generator_change_frequency(app, 1);
                    } else if(event.key == InputKeyUp) {
                        labmate_generator_change_duty(app, 1);
                    } else if(event.key == InputKeyDown) {
                        labmate_generator_change_duty(app, -1);
                    } else if(event.key == InputKeyOk) {
                        if(app->generator_running) {
                            labmate_generator_stop(app);
                        } else {
                            labmate_generator_start(app);
                        }
                    } else if(event.key == InputKeyBack) {
                        /* TIM1/PA7 remains owned in the background until STOP or exit. */
                        app->screen = LabMateScreenMenu;
                    }
                }

}

