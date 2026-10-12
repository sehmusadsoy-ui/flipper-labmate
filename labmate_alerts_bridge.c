#include "labmate_alerts_bridge.h"
#include "labmate_threshold.h"

/* App-thread validation between sampled instruments and pure threshold logic. */
/* A single alert watches the selected instrument only while its measurement
 * is live. Inactive/held/stopped tools cannot generate false threshold trips.
 * The pure threshold module owns compare/latch logic; no ISR or HAL writes.
 */
void threshold_update_from_measurement(LabMateApp* app) {
    if(!app->threshold.armed) return;
    bool valid = false;
    uint64_t sample = 0U;
    switch(app->threshold.source) {
    case LabMateAlertFrequency:
        valid = app->screen == LabMateScreenFrequency && !app->hold &&
                (app->frequency_hw_active || app->frequency_irq_active) &&
                app->frequency_valid;
        if(valid) sample = app->frequency_millihz / 1000U; /* floor Hz */
        break;
    case LabMateAlertPulseDuty:
        valid = app->screen == LabMateScreenPulse && !app->hold &&
                app->pulse_irq_active && app->pulse_period_valid;
        if(valid) sample = app->pulse_duty_permille / 10U; /* floor percent */
        break;
    case LabMateAlertCounter:
        valid = app->screen == LabMateScreenCounter && app->counter_active &&
                app->capture_owner == LabMateCaptureCounter;
        if(valid) sample = app->counter_total;
        break;
    case LabMateAlertButtonSettle:
        valid = app->screen == LabMateScreenButton && app->button_active &&
                app->capture_owner == LabMateCaptureButton &&
                (app->button_stats.presses > 0U || app->button_stats.releases > 0U);
        if(valid) sample = app->button_settle_ms;
        break;
    default:
        break;
    }
    labmate_threshold_update(&app->threshold, valid, sample);
}

