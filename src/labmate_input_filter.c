#include "labmate_input_filter.h"

bool labmate_input_prefilter(LabMateApp* app, FuriStatus status, InputEvent* event) {
    if(!app || !event || status != FuriStatusOk) return true;
    /* The splash consumes its own key; leave that policy to the dispatcher. */
    if(app->ui_splash) return true;

    if(event->type == InputTypePress) {
        app->ui_repeat_streak = 0U;
    } else if(event->type == InputTypeRepeat) {
        const bool vertical =
            event->key == InputKeyUp || event->key == InputKeyDown;
        const bool horizontal =
            event->key == InputKeyLeft || event->key == InputKeyRight;
        bool editor = false;
        if(app->screen == LabMateScreenAlerts) {
            /* Armed: Down acknowledges and limits are locked. No repeat. */
            editor = vertical && !app->threshold.armed;
        } else if(app->screen == LabMateScreenGenerator) {
            editor = horizontal && app->generator_editing;
        } else if(app->screen == LabMateScreenDoctor) {
            editor = vertical && app->doctor_setup_ui.editing &&
                     !app->doctor_show_advice && !app->doctor_show_symptoms &&
                     app->doctor_panel.field != LabMateDoctorFieldSource;
        }
        if(!editor) return true; /* dispatcher ignores Repeat as before */
        if(app->ui_repeat_streak < UINT8_MAX) ++app->ui_repeat_streak;
        /* Reuse each screen's own single-step event type. */
        event->type = app->screen == LabMateScreenAlerts ?
            InputTypePress : InputTypeShort;
    }

    if(app->screen == LabMateScreenDoctor && app->doctor_skip_entry_ok &&
       (event->type == InputTypeShort || event->type == InputTypeLong)) {
        app->doctor_skip_entry_ok = false;
        if(event->key == InputKeyOk) return false;
    }
    return true;
}

void labmate_input_postfilter(
    LabMateApp* app, FuriStatus status, const InputEvent* event,
    LabMateScreen screen_before) {
    if(!app || !event || status != FuriStatusOk) return;
    /* Signal Doctor is opened on OK Press but reads Short/Long. Arm the
     * one-shot guard only for that exact transition. */
    if(screen_before != LabMateScreenDoctor &&
       app->screen == LabMateScreenDoctor &&
       event->type == InputTypePress && event->key == InputKeyOk) {
        app->doctor_skip_entry_ok = true;
    } else if(app->screen != LabMateScreenDoctor) {
        app->doctor_skip_entry_ok = false;
    }
}
