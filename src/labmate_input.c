#include <furi.h>
#include <input/input.h>
#include "labmate_input.h"
#include "labmate_input_tools.h"
#include "labmate_scope_bridge.h"

/* Furi InputTypeShort handles PWM on release; the other tools retain
 * the v1.7 InputTypePress policy. No hardware/SD work is done here.
 */
void labmate_input_dispatch(LabMateApp* app, FuriStatus status,
                            InputEvent event, LabMateDeferredWork* work) {
    if(status != FuriStatusOk) return;
    if(app->screen == LabMateScreenGenerator) {
        if(event.type != InputTypeShort && event.type != InputTypeLong) return;
    } else if(event.type != InputTypePress) {
        return;
    }

    switch(app->screen) {
    case LabMateScreenMenu:
        labmate_input_menu(app, event, work);
        break;
    case LabMateScreenProfiles:
        labmate_input_profiles(app, event, work);
        break;
    case LabMateScreenHistory:
        labmate_input_history(app, event, work);
        break;
    case LabMateScreenHistoryDetail:
        labmate_input_history_detail(app, event, work);
        break;
    case LabMateScreenAbout:
        labmate_input_about(app, event, work);
        break;
    case LabMateScreenAlerts:
        labmate_input_alerts(app, event, work);
        break;
    case LabMateScreenButton:
        labmate_input_button(app, event, work);
        break;
    case LabMateScreenCounter:
        labmate_input_counter(app, event, work);
        break;
    case LabMateScreenLogger:
        labmate_input_logger(app, event, work);
        break;
    case LabMateScreenGpio:
    case LabMateScreenFrequency:
    case LabMateScreenPulse:
        labmate_input_gpio(app, event, work);
        break;
    case LabMateScreenGenerator:
        labmate_input_generator(app, event, work);
        break;
    case LabMateScreenUart:
        labmate_input_uart(app, event, work);
        break;
    case LabMateScreenOneWire:
        labmate_input_onewire(app, event, work);
        break;
    case LabMateScreenI2c:
        labmate_input_i2c(app, event, work);
        break;
    case LabMateScreenDashboard:
        /* No ISR, storage or native resource acquisition in read-only dashboard. */
        if(event.key == InputKeyBack) app->screen = LabMateScreenMenu;
        else if(event.key == InputKeyOk)
            app->dashboard_details = !app->dashboard_details;
        else if(event.key == InputKeyUp)
            app->dashboard_source = (uint8_t)(
                (app->dashboard_source + LabMateSnapshotSourceCount - 1U) %
                LabMateSnapshotSourceCount);
        else if(event.key == InputKeyDown)
            app->dashboard_source = (uint8_t)(
                (app->dashboard_source + 1U) % LabMateSnapshotSourceCount);
        else if(event.key == InputKeyLeft || event.key == InputKeyRight)
            app->dashboard_source = app->dashboard_source < 3U ? 3U : 0U;
        break;
    case LabMateScreenDoctor:
        /* UI mutex is already held; no ISR, HAL, SD or capture operations. */
        if(event.key == InputKeyBack) app->screen = LabMateScreenMenu;
        else if(event.key == InputKeyLeft)
            labmate_doctor_panel_move(&app->doctor_panel, -1);
        else if(event.key == InputKeyRight)
            labmate_doctor_panel_move(&app->doctor_panel, 1);
        else if(event.key == InputKeyUp)
            labmate_doctor_panel_edit(&app->doctor_panel, 1);
        else if(event.key == InputKeyDown)
            labmate_doctor_panel_edit(&app->doctor_panel, -1);
        else if(event.key == InputKeyOk)
            labmate_doctor_panel_step(&app->doctor_panel);
        break;
    case LabMateScreenScope:
        labmate_scope_bridge_input(app, event);
        break;
    default:
        if(event.key == InputKeyBack) app->screen = LabMateScreenMenu;
        break;
    }
}
