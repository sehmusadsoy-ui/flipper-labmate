#include <furi.h>
#include <input/input.h>
#include "labmate_input.h"
#include "labmate_input_tools.h"

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
    default:
        if(event.key == InputKeyBack) app->screen = LabMateScreenMenu;
        break;
    }
}
