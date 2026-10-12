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

/* State transitions and queued requests only; callers hold the UI mutex. */
void labmate_input_dispatch(LabMateApp* app, FuriStatus status,
                            InputEvent event, LabMateDeferredWork* work) {
        /* Generator uses SHORT on key release, so LONG OK can enter the
         * STOP-only custom editor without an accidental START on press.
         * Existing tools preserve their original InputTypePress behavior.
         */
        if(status == FuriStatusOk &&
           ((app->screen == LabMateScreenGenerator &&
             (event.type == InputTypeShort || event.type == InputTypeLong)) ||
            (app->screen != LabMateScreenGenerator &&
             event.type == InputTypePress))) {

            if(app->screen ==
               LabMateScreenMenu) {
                /* One navigation source defines both renderer and key map.
                 * The seven original launch actions remain unchanged.
                 */
                const uint8_t count = app->menu_in_group ?
                    labmate_nav_group_size(app->menu_group) :
                    (uint8_t)LabMateGroupCount;
                if(event.key == InputKeyUp) {
                    app->selected = labmate_nav_wrap(app->selected, count, -1);
                } else if(event.key == InputKeyDown) {
                    app->selected = labmate_nav_wrap(app->selected, count, 1);
                } else if(event.key == InputKeyOk) {
                    if(!app->menu_in_group) {
                        if(app->selected < LabMateGroupCount) {
                            app->menu_group = app->selected;
                            app->selected = 0U;
                            app->menu_in_group = true;
                        }
                    } else if(app->selected < count) {
                    switch(labmate_nav_tool_at(app->menu_group, app->selected)) {
                    case LabMateToolGpio:
                        app->screen =
                            LabMateScreenGpio;
                        app->hold = false;
                        labmate_gpio_activate(app);
                        break;

                    case LabMateToolFrequency:
                        app->screen =
                            LabMateScreenFrequency;
                        app->hold = false;

                        app->gpio_index = app->preferred_frequency_pin;
                        frequency_stats_reset(app);
                        measurement_reset(app);
                        /* A loaded profile may select PC1 LOW instead of PB3 HIGH.
                         * Start the capture engine that owns the selected pin. */
                        if(app->gpio_index == 4U) {
                            labmate_frequency_high_start(app);
                        } else {
                            labmate_frequency_low_start(app);
                        }
                        break;

                    case LabMateToolPulse:
                        app->screen =
                            LabMateScreenPulse;
                        app->hold = false;
                        /* Previous tools may have left PB3/PC3 selected. */
                        app->gpio_index = app->preferred_pulse_pin;
                        app->pulse_stats_view = false;
                        pulse_stats_reset(app);
                        measurement_reset(app);
                        labmate_pulse_capture_start(app);
                        break;

                    case LabMateToolButton:
                        app->screen = LabMateScreenButton;
                        app->button_details_view = false;
                        app->gpio_index = LABMATE_MONITOR_PC1_INDEX;
                        app->capture_blocked = false;
                        labmate_button_capture_reset(app); /* No IRQ until OK RUN */
                        break;

                    case LabMateToolCounter:
                        /* Counter remains STOP until an explicit OK press. */
                        app->screen = LabMateScreenCounter;
                        app->hold = false;
                        app->capture_blocked = false;
                        app->gpio_index = 4U; /* PB3 -> TIM2_CH2 hardware input */
                        labmate_event_counter_reset(app);
                        break;

                    case LabMateToolAlerts:
                        app->screen = LabMateScreenAlerts;
                        break;

                    case LabMateToolGenerator:
                        app->screen = LabMateScreenGenerator;
                        /* InputTypeShort from the menu OK must not start PWM. */
                        app->generator_skip_entry_ok = true;
                        break;

                    case LabMateToolLogger:
                        app->screen = LabMateScreenLogger;
                        /* Preserve logger source selected or loaded. */
                        app->logger_error = false;
                        app->logger_rows = 0U;
                        app->logger_path[0] = '\0';
                        labmate_logger_capture_start(app);
                        break;

                    case LabMateToolHistory:
                        app->screen = LabMateScreenHistory;
                        app->history_busy = true;
                        app->history_error = false;
                        app->history_delete_mode = false;
                        app->history_delete_confirm = false;
                        app->history_delete_notice = 0U;
                        work->history_scan_requested = true;
                        break;

                    case LabMateToolAbout:
                        app->screen = LabMateScreenAbout;
                        app->about_page = 0U;
                        break;

                    case LabMateToolProfiles:
                        app->screen = LabMateScreenProfiles;
                        app->profile_selected = 0U;
                        app->profile_action = 0U; /* LOAD */
                        app->profile_confirm = false;
                        app->profile_notice = 0U;
                        app->profile_busy = true;
                        work->profiles_read_requested = true;
                        break;
                    }
                    }
                } else if(event.key == InputKeyBack) {
                    if(app->menu_in_group) {
                        app->menu_in_group = false;
                        app->selected = app->menu_group;
                    } else {
                        app->running = false;
                    }
                }

            } else if(app->screen == LabMateScreenProfiles) {
                if(!app->profile_busy) {
                    if(app->profile_confirm) {
                        if(event.key == InputKeyBack) {
                            app->profile_confirm = false;
                        } else if(event.key == InputKeyOk &&
                                  (app->profile_io == LabMateProfileIoOk ||
                                   app->profile_io == LabMateProfileIoEmpty)) {
                            /* Recheck at final confirmation: no SD mutation while
                             * PWM or an input/logger resource remains active. */
                            if(app->generator_running ||
                               app->capture_owner != LabMateCaptureNone ||
                               app->logger_recording) {
                                app->profile_notice = app->generator_running ? 4U : 8U;
                                app->profile_confirm = false;
                            } else {
                            /* Snapshot under mutex. Commit SD only afterward. */
                            work->proposed_profiles = app->profiles;
                            LabMateProfile* profile =
                                &work->proposed_profiles.slots[app->profile_selected];
                            work->profiles_delete_requested = app->profile_action == 2U;
                            if(work->profiles_delete_requested) {
                                /* Canonical empty slot: all 5 fields zero.
                                 * The inactive CRC copy gets a new generation;
                                 * the active copy is never touched by DELETE.
                                 */
                                memset(profile, 0, sizeof(*profile));
                            } else {
                                profile->present = true;
                                profile->frequency_pin = app->preferred_frequency_pin;
                                profile->pulse_pin = app->preferred_pulse_pin;
                                profile->generator_index = app->generator_freq_index;
                                profile->logger_source = app->logger_source;
                            }
                            work->proposed_profiles.generation++;
                            work->proposed_copy = app->profile_active_copy;
                            work->profiles_save_requested = true;
                            app->profile_busy = true;
                            app->profile_confirm = false;
                            app->profile_notice = 0U;
                            }
                        }
                    } else if(event.key == InputKeyUp) {
                        app->profile_selected = labmate_nav_wrap(
                            app->profile_selected, LABMATE_PROFILE_SLOT_COUNT, -1);
                        app->profile_notice = 0U;
                    } else if(event.key == InputKeyDown) {
                        app->profile_selected = labmate_nav_wrap(
                            app->profile_selected, LABMATE_PROFILE_SLOT_COUNT, 1);
                        app->profile_notice = 0U;
                    } else if(event.key == InputKeyLeft ||
                              event.key == InputKeyRight) {
                        app->profile_action = event.key == InputKeyRight ?
                            (uint8_t)((app->profile_action + 1U) % 3U) :
                            (uint8_t)((app->profile_action + 2U) % 3U);
                        app->profile_notice = 0U;
                    } else if(event.key == InputKeyOk) {
                        /* A blocked LOAD must not become an active SAVE/DELETE
                         * merely because LEFT/RIGHT changed the action. */
                        if(app->generator_running ||
                           app->capture_owner != LabMateCaptureNone ||
                           app->logger_recording) {
                            app->profile_notice = app->generator_running ? 4U : 8U;
                        } else if(app->profile_io != LabMateProfileIoOk &&
                                  app->profile_io != LabMateProfileIoEmpty) {
                            /* Do not overwrite fully corrupt or unreadable SD. */
                        } else if(app->profile_action == 1U ||
                                  app->profile_action == 2U) {
                            /* Delete on EMPTY is a no-op: never write SD.
                             * Both SAVE and DELETE need a second OK press.
                             */
                            if(app->profile_action == 2U &&
                               !app->profiles.slots[app->profile_selected].present) {
                                app->profile_notice = 3U; /* EMPTY */
                            } else if(app->profile_action == 1U &&
                                      app->generator_freq_index >=
                                          LABMATE_PROFILE_GENERATOR_PRESETS) {
                                /* Legacy 32-byte profile codec cannot encode CUSTOM.
                                 * Refuse rather than write an invalid CRC profile.
                                 */
                                app->profile_notice = 7U; /* PRESET ONLY */
                            } else {
                                app->profile_confirm = true;
                            }
                        } else {
                            const LabMateProfile* profile =
                                &app->profiles.slots[app->profile_selected];
                            if(!profile->present) {
                                app->profile_notice = 3U; /* EMPTY */
                            } else {
                                /* LOAD never starts PWM or arms an IRQ. */
                                app->preferred_frequency_pin = profile->frequency_pin;
                                app->preferred_pulse_pin = profile->pulse_pin;
                                app->generator_freq_index = profile->generator_index;
                                /* v1 profile files do not contain PWM duty. */
                                app->generator_duty_percent = LABMATE_PWM_DEFAULT_DUTY;
                                app->logger_source = profile->logger_source;
                                app->profile_notice = 2U; /* LOADED */
                            }
                        }
                    } else if(event.key == InputKeyBack) {
                        app->screen = LabMateScreenMenu;
                    }
                }
            } else if(app->screen == LabMateScreenHistory) {
                if(app->history_busy) {
                    /* Ignore input while an SD operation is in progress. */
                } else if(app->history_delete_confirm) {
                    if(event.key == InputKeyBack) {
                        app->history_delete_confirm = false;
                    } else if(event.key == InputKeyOk &&
                              app->history_selected < app->history_count) {
                        /* Snapshot selected ID under lock, not a path.
                         * Do not remove files while any reader/writer owns
                         * a storage handle; perform I/O outside mutex.
                         */
                        if(app->logger_recording || app->logger_busy ||
                           app->logger_file || app->logger_storage ||
                           app->history_file || app->history_storage) {
                            app->history_delete_notice = 2U;
                            app->history_delete_confirm = false;
                        } else {
                            work->history_delete_id =
                                app->history_ids[app->history_selected];
                            work->history_delete_selected = app->history_selected;
                            work->history_delete_requested = true;
                            app->history_delete_confirm = false;
                            app->history_delete_notice = 0U;
                            app->history_busy = true;
                        }
                    }
                } else if(event.key == InputKeyUp && app->history_count > 0U) {
                    app->history_selected = (uint8_t)(
                        (app->history_selected + app->history_count - 1U) %
                        app->history_count);
                    app->history_delete_notice = 0U;
                } else if(event.key == InputKeyDown && app->history_count > 0U) {
                    app->history_selected = (uint8_t)(
                        (app->history_selected + 1U) % app->history_count);
                    app->history_delete_notice = 0U;
                } else if((event.key == InputKeyLeft ||
                           event.key == InputKeyRight) &&
                          !app->history_error && app->history_count > 0U) {
                    app->history_delete_mode = !app->history_delete_mode;
                    app->history_delete_notice = 0U;
                } else if(event.key == InputKeyOk &&
                          !app->history_error && app->history_count > 0U) {
                    if(app->history_delete_mode) {
                        app->history_delete_confirm = true;
                        app->history_delete_notice = 0U;
                    } else {
                        app->screen = LabMateScreenHistoryDetail;
                        app->history_busy = true;
                        work->history_open_requested = true;
                    }
                } else if(event.key == InputKeyBack) {
                    app->history_delete_mode = false;
                    app->history_delete_confirm = false;
                    app->screen = LabMateScreenMenu;
                }
            } else if(app->screen == LabMateScreenHistoryDetail) {
                if(event.key == InputKeyBack) {
                    app->screen = LabMateScreenHistory;
                    app->history_loading = false;
                    work->history_close_requested = true;
                }
            } else if(app->screen == LabMateScreenAbout) {
                /* Pure UI paging. Never touches capture/GPIO or stored profiles. */
                if(event.key == InputKeyRight || event.key == InputKeyDown) {
                    app->about_page = labmate_nav_wrap(
                        app->about_page, (uint8_t)(LabMateToolCount + 2U), 1);
                } else if(event.key == InputKeyLeft || event.key == InputKeyUp) {
                    app->about_page = labmate_nav_wrap(
                        app->about_page, (uint8_t)(LabMateToolCount + 2U), -1);
                } else if(event.key == InputKeyBack) {
                    app->screen = LabMateScreenMenu;
                }

            } else if(app->screen == LabMateScreenAlerts) {
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

            } else if(app->screen == LabMateScreenButton) {
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

            } else if(app->screen == LabMateScreenCounter) {
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

            } else if(app->screen == LabMateScreenLogger) {
                if(event.key == InputKeyLeft) {
                    labmate_logger_capture_change(app, -1);
                } else if(event.key == InputKeyRight) {
                    labmate_logger_capture_change(app, 1);
                } else if(event.key == InputKeyOk) {
                    work->logger_stop_requested = app->logger_recording;
                    work->logger_start_requested = !app->logger_recording;
                    app->logger_busy = true;
                    app->logger_busy_stopping = work->logger_stop_requested;
                    if(work->logger_stop_requested) app->logger_recording = false;
                } else if(event.key == InputKeyBack) {
                    if(app->logger_recording || app->logger_file || app->logger_storage) {
                        work->logger_stop_requested = true;
                        app->logger_recording = false;
                        app->logger_busy = true;
                        app->logger_busy_stopping = true;
                    }
                    labmate_logger_capture_stop(app);
                    app->screen = LabMateScreenMenu;
                }

            } else if(
                labmate_screen_uses_gpio(
                    app->screen)) {

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

            } else if(app->screen == LabMateScreenGenerator) {
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

            } else {
                if(event.key == InputKeyBack) {
                    app->screen =
                        LabMateScreenMenu;
                }
            }
        }

}
