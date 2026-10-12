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
void labmate_input_profiles(LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {

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
}

