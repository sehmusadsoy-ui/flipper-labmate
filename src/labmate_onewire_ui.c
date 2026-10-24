#include "labmate_ui_screens.h"
#include "labmate_ui_primitives.h"
#include <stdio.h>

void draw_onewire(Canvas* canvas, LabMateApp* app) {
    const LabMateOneWireHw* s = &app->thermometer;
    const char* label = "READY";
    const char* message = "EXT. VDD REQUIRED";
    const bool active = s->status == LabMateOneWireHwConverting;
    /* The driver accepts only converted DS18B20 data in [-55, +125] C
     * at 9..12 bit resolution. Reject inconsistent snapshots rather than
     * displaying an impossible sensor value as a successful reading. */
    const bool valid_temperature = s->has_temperature &&
        s->temperature_tenths >= -550 && s->temperature_tenths <= 1250 &&
        s->resolution_bits >= 9U && s->resolution_bits <= 12U;
    switch(s->status) {
    case LabMateOneWireHwConverting:
        label = "RUN";
        message = "CONVERTING...";
        break;
    case LabMateOneWireHwMeasured:
        label = valid_temperature ? "DONE" : "ERR";
        message = valid_temperature ? "DS18B20 CRC OK" :
                  (s->has_temperature ? "INVALID TEMP DATA" : "NO VALID SAMPLE");
        break;
    case LabMateOneWireHwNoSensor:
        label = "NONE";
        message = "NO SENSOR ON PA4";
        break;
    case LabMateOneWireHwBusy:
        label = "BUSY";
        message = "STOP OTHER TOOLS";
        break;
    case LabMateOneWireHwDataError:
        label = "ERROR";
        message = "CRC / DATA INVALID";
        break;
    case LabMateOneWireHwPowerCheck:
        label = "PWR";
        message = "85C? CHECK POWER";
        break;
    case LabMateOneWireHwStopped:
        label = "STOP";
        message = "MEASUREMENT HALTED";
        break;
    default:
        break;
    }

    ui_draw_header(canvas, "1-WIRE TEMP");
    ui_badge(canvas, 91, 1, 35, label, active);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 3, 22, "PA4 DQ / 3.3V");
    canvas_draw_str(canvas, 3, 32, "EXTERNAL VDD ONLY");
    canvas_draw_line(canvas, 2, 35, 126, 35);

    if(s->status == LabMateOneWireHwMeasured && valid_temperature) {
        const int32_t value = s->temperature_tenths;
        const uint32_t magnitude = (uint32_t)(value < 0 ? -value : value);
        char text[32];
        snprintf(text, sizeof(text), "%s%lu.%lu C / %ubit",
                 value < 0 ? "-" : "",
                 (unsigned long)(magnitude / 10U),
                 (unsigned long)(magnitude % 10U),
                 (unsigned)s->resolution_bits);
        canvas_draw_str(canvas, 3, 45, text);
    } else {
        canvas_draw_str(canvas, 3, 45, message);
    }
    ui_footer_pair(canvas, "OK", active ? "STOP" : "READ", "BACK", "MENU");
}
