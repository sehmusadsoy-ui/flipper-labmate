#include "labmate_ui_screens.h"
#include "labmate_comm_ui.h"
#include <stdio.h>

/* COMM Step 4 — visual-only DS18B20 temperature instrument.
 * No OneWireHost/GPIO/CRC/power/session/input behavior is modified here.
 * The hardware driver remains the sole authority on temperature validity. */
void draw_onewire(Canvas* canvas, LabMateApp* app) {
    const LabMateOneWireHw* s = &app->thermometer;
    const bool active = s->status == LabMateOneWireHwConverting;
    const bool measured = s->status == LabMateOneWireHwMeasured;
    const bool valid_temperature = s->has_temperature &&
        s->temperature_tenths >= -550 && s->temperature_tenths <= 1250 &&
        s->resolution_bits >= 9U && s->resolution_bits <= 12U;
    const bool done = measured && valid_temperature;
    const bool no_reply = s->status == LabMateOneWireHwNoSensor;
    const bool busy = s->status == LabMateOneWireHwBusy;
    const bool power_check = s->status == LabMateOneWireHwPowerCheck;
    const bool data_error = s->status == LabMateOneWireHwDataError ||
                             (measured && !valid_temperature);
    const bool stopped = s->status == LabMateOneWireHwStopped;

    /* Distinguish power/CRC/bus ownership from "No reply": do not turn a
     * CRC error, power-on 85C warning or failed firmware lease into a
     * false no-sensor diagnosis. Keep the proven UI-kit glyph shapes. */
    const UiKitInstrumentState instrument_state =
        active ? UiKitInstrumentLive :
        done ? UiKitInstrumentDone :
        no_reply ? UiKitInstrumentNoReply :
        busy ? UiKitInstrumentBusy :
        (power_check || data_error) ? UiKitInstrumentError :
        stopped ? UiKitInstrumentStopped : UiKitInstrumentReady;
    const bool pulse = (app->ui_frame & 16U) != 0U;

    /* Exact header first. Some real state-chip/title combinations cannot
     * share a row at FontPrimary: fallback to the complete title with
     * FontSecondary, then the short "1-Wire" if truly necessary. Neither
     * approach shifts an element more than 2px or clips a glyph. */
    if(!ui_kit_pixel_header(canvas, "1-Wire temp", true, instrument_state, pulse)) {
        const uint8_t chip_w = ui_kit_state_chip_width(canvas, instrument_state);
        if(!chip_w) return;
        const uint16_t chip_x = (uint16_t)(127U - chip_w);
        canvas_set_font(canvas, FontSecondary);
        const uint16_t full_w = canvas_string_width(canvas, "1-Wire temp");
        const bool fits_at_nine = 9U + full_w + 1U <= chip_x;
        const bool fits_at_seven = 7U + full_w + 1U <= chip_x;
        const uint8_t title_x = fits_at_nine ? 9U : fits_at_seven ? 7U : 9U;
        const char* title = (fits_at_nine || fits_at_seven) ?
            "1-Wire temp" : "1-Wire";
        canvas_set_font(canvas, (fits_at_nine || fits_at_seven) ?
                        FontSecondary : FontPrimary);
        if((uint32_t)title_x + canvas_string_width(canvas, title) + 1U > chip_x)
            return; /* refuse title/status collision */
        canvas_set_color(canvas, ColorBlack);
        canvas_draw_line(canvas, 5U, 2U, 2U, 5U);
        canvas_draw_line(canvas, 2U, 5U, 5U, 8U);
        canvas_draw_str(canvas, title_x, 9U, title);
        (void)ui_kit_state_chip(canvas, instrument_state, pulse);
    }

    /* Single context row and shared 3.3 V tag. Tag is power/wiring
     * INFORMATION, not a request to enable a GPIO/OTG supply. */
    canvas_set_font(canvas, FontSecondary);
    const uint16_t tag_w = canvas_string_width(canvas, "3.3 V") + 8U;
    const uint16_t tag_left = 124U - tag_w;
    if(4U + canvas_string_width(canvas, "DQ pin PA4") + 2U <= tag_left)
        canvas_draw_str(canvas, 4U, 20U, "DQ pin PA4");
    (void)ui_kit_tag(canvas, 123U, 12U, "3.3 V");

    /* One line per real state, no duplicate VDD warnings and no fabricated
     * temperature, resolution or successful CRC on incomplete reads. */
    const char* description = done ? "Temperature" :
        no_reply ? "Check DQ wiring and power" :
        active ? "Reading temperature..." :
        busy ? "Another tool is using PA4" :
        power_check ? "Check external VDD power" :
        data_error ? "Invalid temperature data" :
        stopped ? "Measurement stopped" :
        "Needs external VDD power";
    const char* shorter = done ? "Temperature" :
        no_reply ? "Check DQ and power" :
        active ? "Reading sensor..." :
        busy ? "PA4 is busy" :
        power_check ? "Check VDD power" :
        data_error ? "Invalid data" :
        stopped ? "Stopped" :
        "External VDD needed";

    canvas_set_font(canvas, FontSecondary);
    const uint16_t description_w = canvas_string_width(canvas, description);
    if(description_w > 118U) description = shorter;
    if(canvas_string_width(canvas, description) <= 118U)
        canvas_draw_str(canvas, 5U, 31U, description);

    if(done) {
        char bits[16];
        snprintf(bits, sizeof(bits), "%u-bit", (unsigned)s->resolution_bits);
        canvas_set_font(canvas, FontSecondary);
        const uint16_t bits_w = canvas_string_width(canvas, bits);
        if(bits_w && bits_w <= 119U)
            canvas_draw_str(canvas, 123U - bits_w, 31U, bits);
    }

    /* Fixed FontBigNumbers hero: a missing/invalid/unread sample always
     * draws --.-, never stale measured numbers or guessed room temperature.
     * DS18B20 tenths are signed; INT16_MIN-safe int32 magnitude conversion. */
    char numeric[20];
    if(done) {
        const int32_t value = s->temperature_tenths;
        const uint32_t magnitude = (uint32_t)(value < 0 ? -value : value);
        snprintf(numeric, sizeof(numeric), "%s%lu.%lu",
                 value < 0 ? "-" : "",
                 (unsigned long)(magnitude / 10U),
                 (unsigned long)(magnitude % 10U));
    } else {
        snprintf(numeric, sizeof(numeric), "--.-");
    }

    /* Use FontBigNumbers for the complete numeric token when supported and
     * fitting; otherwise use whole FontPrimary text, never partial glyphs.
     * The 1px degree-ring is procedural and font-independent. */
    canvas_set_font(canvas, FontBigNumbers);
    uint16_t numeric_w = canvas_string_width(canvas, numeric);
    canvas_set_font(canvas, FontPrimary);
    const uint16_t unit_w = canvas_string_width(canvas, "C");
    const uint16_t right_edge = 4U + numeric_w + 9U + unit_w;
    if(!numeric_w || right_edge > 127U) {
        canvas_set_font(canvas, FontPrimary);
        numeric_w = canvas_string_width(canvas, numeric);
    } else {
        canvas_set_font(canvas, FontBigNumbers);
    }
    if(numeric_w && 4U + numeric_w + 9U + unit_w <= 127U) {
        canvas_set_color(canvas, ColorBlack);
        canvas_draw_str(canvas, 4U, 49U, numeric);
        const uint8_t degree_x = (uint8_t)(4U + numeric_w + 5U);
        canvas_draw_dot(canvas, degree_x, 35U);
        canvas_draw_dot(canvas, degree_x-1U, 36U);
        canvas_draw_dot(canvas, degree_x+1U, 36U);
        canvas_draw_dot(canvas, degree_x, 37U);
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str(canvas, 4U + numeric_w + 9U, 49U, "C");
    }

    /* The existing input handler actually stops active conversion on OK.
     * All states leave BACK navigation intact; BACK is never shown as a
     * redundant bottom chip. */
    (void)ui_kit_key_hint(canvas, 4U, UiKitKeyOk,
                          active ? "Stop" : done ? "Read again" : "Read");
    canvas_set_color(canvas, ColorBlack);
}
