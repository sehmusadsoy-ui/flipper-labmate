#include "labmate_ui_screens.h"
#include "labmate_comm_ui.h"
#include <stdio.h>

/* Passive temperature presentation; the driver owns PA4 and validity. */
void draw_onewire(Canvas* canvas, LabMateApp* app) {
    const LabMateOneWireHw* s = &app->thermometer;
    const char* label = "READY";
    const char* message = "EXT. VDD REQUIRED";
    const bool active = s->status == LabMateOneWireHwConverting;
    /* Only converted DS18B20 [-55,+125] C / 9..12-bit samples are valid. */
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

    labmate_comm_ui_header(canvas, "1-Wire temp", label, active);
    canvas_set_font(canvas, FontSecondary);
    canvas_set_color(canvas, ColorBlack);
    (void)ui_kit_text(canvas, 4U, 20U, 120U, "PA4 DQ / 3.3V", NULL);
    (void)ui_kit_text(canvas, 4U, 30U, 120U, "EXTERNAL VDD ONLY", NULL);

    if(s->status == LabMateOneWireHwMeasured && valid_temperature) {
        const int32_t value = s->temperature_tenths;
        const uint32_t magnitude = (uint32_t)(value < 0 ? -value : value);
        char numeric[24], bits[16];
        snprintf(numeric, sizeof(numeric), "%s%lu.%lu",
                 value < 0 ? "-" : "",
                 (unsigned long)(magnitude / 10U),
                 (unsigned long)(magnitude % 10U));
        snprintf(bits, sizeof(bits), "%ubit", (unsigned)s->resolution_bits);
        canvas_set_font(canvas, FontBigNumbers);
        const uint16_t wide = canvas_string_width(canvas, numeric);
        if(wide > 88U) canvas_set_font(canvas, FontPrimary);
        if(canvas_string_width(canvas, numeric) <= 88U)
            canvas_draw_str(canvas, 4U, 50U, numeric);
        canvas_set_font(canvas, FontSecondary);
        canvas_draw_str(canvas, 102U, 42U, "C");
        (void)ui_kit_text(canvas, 94U, 51U, 32U, bits, NULL);
    } else {
        (void)ui_kit_text(canvas, 4U, 45U, 120U, message, NULL);
    }

    labmate_comm_ui_keys(canvas, UiKitKeyOk, active ? "Stop" : "Read",
                         UiKitKeyBack, "Menu");
}
