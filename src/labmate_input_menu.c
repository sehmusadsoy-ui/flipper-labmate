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
#include "labmate_uart.h"
#include "labmate_scope_bridge.h"
void labmate_input_menu(LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {

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
                        /* New capture intent invalidates earlier Doctor evidence. */
                        labmate_dashboard_store_init(&app->doctor_store);
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
                        labmate_dashboard_store_init(&app->doctor_store);
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

                    case LabMateToolUart:
                        app->screen = LabMateScreenUart;
                        labmate_uart_reenter(&app->uart);
                        break;

                    case LabMateToolDoctor:
                        /* No GPIO, IRQ, capture start, timer or storage access. */
                        app->screen = LabMateScreenDoctor;
                        break;

                    case LabMateToolScope:
                        app->screen = LabMateScreenScope;
                        labmate_scope_bridge_enter(app);
                        break;

                    case LabMateToolI2c:
                        labmate_i2c_runtime_stop(app->i2c);
                        app->i2c_page = 0U;
                        app->screen = LabMateScreenI2c;
                        break;

                    case LabMateToolOneWire:
                        /* No pin configuration until explicit OK on sensor page. */
                        labmate_onewire_hw_stop(&app->thermometer);
                        labmate_onewire_hw_init(&app->thermometer);
                        app->screen = LabMateScreenOneWire;
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

}

void labmate_input_about(LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {
    UNUSED(work);

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

}

