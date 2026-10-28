#include <furi.h>
#include <input/input.h>
#include "labmate_input.h"
#include "labmate_input_tools.h"
#include "labmate_scope_bridge.h"
#include "labmate_ui_motion.h"
#include "labmate_settings.h"

/* Furi InputTypeShort handles PWM on release; the other tools retain
 * the v1.7 InputTypePress policy. No hardware/SD work is done here.
 */
void labmate_input_dispatch(LabMateApp* app, FuriStatus status,
                            InputEvent event, LabMateDeferredWork* work) {
    if(status != FuriStatusOk) return;
    /* First press merely dismisses the non-blocking 1.2 s splash. The
     * same key cannot accidentally enter a tool or exit the application. */
    if(app->ui_splash) {
        if(event.type == InputTypePress) app->ui_splash = false;
        return;
    }
    if(app->screen == LabMateScreenDoctor) {
        /* Distinguish short OK (edit) from long OK (help). Processing on
         * Press would enter edit before the long-press event can arrive. */
        if(event.type != InputTypeShort && event.type != InputTypeLong) return;
    } else if(app->screen == LabMateScreenGenerator) {
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
    case LabMateScreenSettings:
        labmate_settings_input(app, event, work);
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
        else if(event.key == InputKeyOk) {
            if(!app->dashboard_details) {
                app->dashboard_details = true;
                app->dashboard_evidence = false;
            } else if(!app->dashboard_evidence) {
                app->dashboard_evidence = true;
            } else {
                app->dashboard_details = false;
                app->dashboard_evidence = false;
            }
        }
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
        /* All advisory/config work remains app-thread UI only. */
        if(!app->doctor_show_advice && !app->doctor_show_symptoms) {
            LabMateDoctorSetupKey key = LabMateDoctorSetupOk;
            switch(event.key) {
            case InputKeyUp: key = LabMateDoctorSetupUp; break;
            case InputKeyDown: key = LabMateDoctorSetupDown; break;
            case InputKeyLeft: key = LabMateDoctorSetupLeft; break;
            case InputKeyRight: key = LabMateDoctorSetupRight; break;
            case InputKeyOk: key = LabMateDoctorSetupOk; break;
            case InputKeyBack: key = LabMateDoctorSetupBack; break;
            default: break;
            }
            if(event.key == InputKeyUp || event.key == InputKeyDown ||
               event.key == InputKeyLeft || event.key == InputKeyRight ||
               event.key == InputKeyOk || event.key == InputKeyBack) {
                const LabMateDoctorSetupAction action = labmate_doctor_setup_key(
                    &app->doctor_setup_ui, &app->doctor_panel, key,
                    event.type == InputTypeLong);
                if(action == LabMateDoctorSetupOpenSignal) {
                    app->doctor_show_advice = true;
                    app->doctor_show_symptoms = false;
                } else if(action == LabMateDoctorSetupExit) {
                    app->screen = LabMateScreenMenu;
                }
            }
        } else if(event.type == InputTypeLong) {
            /* Long OK is for setup explanations, not result navigation. */
        } else if(event.key == InputKeyBack) app->screen = LabMateScreenMenu;
        else if(app->doctor_show_symptoms) {
            /* Scope 4/4: no mutations or GPIO actions from the verdict chip.
             * Left opens Signal; OK returns to genuinely editable settings. */
            if(event.key == InputKeyLeft) {
                app->doctor_show_symptoms = false;
            } else if(event.key == InputKeyOk) {
                app->doctor_show_symptoms = false;
                app->doctor_show_advice = false;
                app->doctor_panel.field = LabMateDoctorFieldSource;
            }
        } else if(app->doctor_show_advice) {
            /* Signal 3/4: Left = Duty, Right = Scope, OK = setup. */
            if(event.key == InputKeyRight)
                app->doctor_show_symptoms = true;
            else if(event.key == InputKeyLeft) {
                app->doctor_show_advice = false;
                app->doctor_panel.field = LabMateDoctorFieldDuty;
            } else if(event.key == InputKeyOk) {
                const LabMateDoctorPanelAssessment a = labmate_doctor_panel_assess(
                    &app->doctor_panel, &app->doctor_store);
                app->doctor_show_advice = false;
                app->doctor_panel.field = a.status == LabMateDoctorPanelSetReference ?
                    LabMateDoctorFieldFrequency :
                    a.status == LabMateDoctorPanelAssessed && a.doctor.evidence_accepted &&
                    a.doctor.verdict == LabMateDoctorDutyDeviation ?
                    LabMateDoctorFieldDuty : LabMateDoctorFieldSource;
            }
        }
        break;
    case LabMateScreenScope:
        labmate_scope_bridge_input(app, event);
        break;
    default:
        if(event.key == InputKeyBack) app->screen = LabMateScreenMenu;
        break;
    }
}
