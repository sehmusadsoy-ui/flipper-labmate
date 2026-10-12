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
void labmate_input_history(LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {

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
}

void labmate_input_history_detail(LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {

                if(event.key == InputKeyBack) {
                    app->screen = LabMateScreenHistory;
                    app->history_loading = false;
                    work->history_close_requested = true;
                }
}

void labmate_input_logger(LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {

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

}

