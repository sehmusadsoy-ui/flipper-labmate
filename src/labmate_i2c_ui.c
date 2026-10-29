#include "labmate_ui_screens.h"
#include "labmate_comm_ui.h"
#include "labmate_i2c_runtime.h"
#include <stdio.h>

/* COMM Step 3: a purely visual I2C dashboard. The actual scanner still
 * scans PC0 SCL / PC1 SDA with bounded firmware bus ownership; the
 * 4-address read-only page and UP/DOWN page input remain unchanged. */
void draw_i2c(Canvas* canvas, LabMateApp* app) {
    LabMateI2cView result;
    const LabMateI2cRuntimeStatus status =
        labmate_i2c_runtime_snapshot(app->i2c, app->i2c_page, &result);
    const bool scanning = status == LabMateI2cRuntimeScanning;
    const bool found = status == LabMateI2cRuntimeResults;
    const bool no_reply = status == LabMateI2cRuntimeNoDevices;
    const bool busy = status == LabMateI2cRuntimeBusy;
    const bool firmware_missing = status == LabMateI2cRuntimeApiMissing;
    const bool failed = status == LabMateI2cRuntimeFailed;
    const bool cancelled = status == LabMateI2cRuntimeCancelled;
    const UiKitInstrumentState instrument_state =
        scanning ? UiKitInstrumentLive :
        no_reply ? UiKitInstrumentNoReply :
        busy ? UiKitInstrumentBusy :
        (firmware_missing || failed) ? UiKitInstrumentError :
        cancelled ? UiKitInstrumentStopped : UiKitInstrumentReady;
    /* ui_frame is a finite carousel tween (normally 6), not an ongoing
     * COMM animation clock. The shared UI pulse phase advances at ~33ms
     * when motion is enabled; toggle the live glyph every 15 phases
     * (~495ms) without timers, delays or hardware effects. */
    const bool pulse = ((app->ui_pulse_phase / 15U) & 1U) != 0U;

    /* The full FontPrimary header cannot geometrically share y=0 with
     * "No reply": preserve the status chip, and prefer the FULL title
     * in FontSecondary if it fits; use a short I2C title only otherwise.
     * A left shift is limited to 2 pixels (x9 -> x7), never overlap. */
    if(!ui_kit_pixel_header(canvas, "I2C explorer", true, instrument_state, pulse)) {
        const uint8_t chip_w = ui_kit_state_chip_width(canvas, instrument_state);
        if(!chip_w) return;
        const uint16_t chip_x = (uint16_t)(127U - chip_w);
        canvas_set_font(canvas, FontSecondary);
        const uint16_t full_w = canvas_string_width(canvas, "I2C explorer");
        const bool at_nine = 9U + full_w + 1U <= chip_x;
        const bool at_seven = 7U + full_w + 1U <= chip_x;
        const uint8_t title_x = at_nine ? 9U : at_seven ? 7U : 9U;
        const char* title = (at_nine || at_seven) ? "I2C explorer" : "I2C";
        canvas_set_font(canvas, (at_nine || at_seven) ?
                        FontSecondary : FontPrimary);
        if((uint32_t)title_x + canvas_string_width(canvas, title) + 1U > chip_x)
            return;
        canvas_set_color(canvas, ColorBlack);
        canvas_draw_line(canvas, 5U, 2U, 2U, 5U);
        canvas_draw_line(canvas, 2U, 5U, 5U, 8U);
        canvas_draw_str(canvas, title_x, 9U, title);
        (void)ui_kit_state_chip(canvas, instrument_state, pulse);
    }

    /* Explicit right-anchored 3.3 V tag. The full pin/signal context is
     * drawn only if it has at least a 2px gap to the tag's left edge.
     * The short variant is required at wide FontSecondary metrics. */
    canvas_set_font(canvas, FontSecondary);
    const uint16_t tag_left =
        (uint16_t)(124U - (canvas_string_width(canvas, "3.3 V") + 8U));
    const uint16_t left_w = canvas_string_width(canvas, "SCL PC0");
    const uint16_t right_w = canvas_string_width(canvas, "SDA PC1");
    const uint16_t dot_x = 4U + left_w + 3U;
    const uint16_t right_x = dot_x + 5U;
    if(right_x + right_w + 2U <= tag_left) {
        canvas_draw_str(canvas, 4U, 20U, "SCL PC0");
        canvas_draw_dot(canvas, dot_x, 17U);
        canvas_draw_str(canvas, right_x, 20U, "SDA PC1");
    } else {
        const char* compact = "SCL0 / SDA1";
        if(4U + canvas_string_width(canvas, compact) + 2U <= tag_left)
            canvas_draw_str(canvas, 4U, 20U, compact);
    }
    (void)ui_kit_tag(canvas, 123U, 12U, "3.3 V");

    canvas_set_color(canvas, ColorBlack);
    canvas_set_font(canvas, FontSecondary);
    if(found) {
        /* The real non-mutating view contains FOUR addresses/page, not
         * eight. It is unsafe to fabricate 4 further ACK results or change
         * the input pagination in a visual-only patch. Use the target's
         * 4-column chip grid with the remaining second row unfilled. */
        for(uint8_t i = 0U; i < result.row_count && i < 4U; ++i) {
            const uint8_t x = (uint8_t)(4U + 31U*(i%4U));
            const uint8_t y = (uint8_t)(24U + 12U*(i/4U));
            char address[8];
            snprintf(address, sizeof(address), "0x%02X", result.row_address[i]);
            canvas_set_font(canvas, FontSecondary);
            const uint16_t w = canvas_string_width(canvas, address);
            if(w > 24U) continue;
            canvas_draw_rframe(canvas, x, y, 28U, 10U, 3U);
            canvas_draw_str(canvas, x + (28U-w)/2U, y + 8U, address);
        }

        char count[8];
        snprintf(count, sizeof(count), "%u", (unsigned)result.found_total);
        canvas_set_font(canvas, FontPrimary);
        const uint16_t count_w = canvas_string_width(canvas, count);
        const bool multiple = result.page_count > 1U;
        const char* summary = result.found_total == 1U ?
            "device found" : "devices found";
        canvas_set_font(canvas, FontSecondary);
        const uint16_t summary_w = canvas_string_width(canvas, summary);
        uint16_t text_end = (uint16_t)(4U + count_w + 3U + summary_w);
        if(multiple) {
            /* Page 1 of 2 must also fit on the same 52px baseline.
             * Abbreviate only the summary, never the page numerator. */
            char page_text[24];
            snprintf(page_text, sizeof(page_text), "Page %u of %u",
                     (unsigned)(result.page + 1U),
                     (unsigned)result.page_count);
            const uint16_t page_w = canvas_string_width(canvas, page_text);
            if(text_end + 3U > 123U - page_w)
                summary = "found";
            const uint16_t shorter_w = canvas_string_width(canvas, summary);
            text_end = (uint16_t)(4U + count_w + 3U + shorter_w);
            if(page_w <= 119U && text_end + 3U <= 123U-page_w)
                canvas_draw_str(canvas, 123U-page_w, 52U, page_text);
        }
        canvas_set_font(canvas, FontSecondary);
        const uint16_t remaining = canvas_string_width(canvas, summary);
        if(4U + count_w + 3U + remaining <= 123U) {
            canvas_set_font(canvas, FontPrimary);
            canvas_draw_str(canvas, 4U, 52U, count);
            canvas_set_font(canvas, FontSecondary);
            canvas_draw_str(canvas, 4U + count_w + 3U, 52U, summary);
        }
    } else {
        canvas_draw_rframe(canvas, 4U, 24U, 120U, 21U, 3U);
        if(status == LabMateI2cRuntimeReady || scanning) {
            /* Animated waveform is a visual indicator ONLY. No wire state
             * is sampled, assumed or modified by these drawing calls. */
            canvas_set_font(canvas, FontSecondary);
            canvas_draw_str(canvas, 8U, 33U, "SCL");
            canvas_draw_str(canvas, 8U, 42U, "SDA");
            if(scanning) {
                const uint8_t phase = (uint8_t)(app->ui_pulse_phase % 10U);
                for(uint8_t x = 30U; x < 118U; ++x) {
                    const uint8_t current = (uint8_t)
                        (((x + phase) % 10U) < 5U ? 28U : 33U);
                    const uint8_t next = (uint8_t)
                        (((x + 1U + phase) % 10U) < 5U ? 28U : 33U);
                    canvas_draw_line(canvas, x, current, x+1U, current);
                    if(current != next)
                        canvas_draw_line(canvas, x+1U, current, x+1U, next);
                }
                canvas_draw_line(canvas, 30U, 41U, 60U, 41U);
                canvas_draw_line(canvas, 60U, 41U, 60U, 38U);
                canvas_draw_line(canvas, 60U, 38U, 80U, 38U);
                canvas_draw_line(canvas, 80U, 38U, 80U, 41U);
                canvas_draw_line(canvas, 80U, 41U, 118U, 41U);
            } else {
                for(uint8_t x = 30U; x <= 118U; x += 2U) {
                    canvas_draw_dot(canvas, x, 28U);
                    canvas_draw_dot(canvas, x, 41U);
                }
            }
        } else {
            const char* title = no_reply ? "No devices found" :
                busy ? "Bus busy" : firmware_missing ? "Firmware API missing" :
                failed ? "Scan error" : cancelled ? "Scan cancelled" : "Ready";
            const char* explanation = no_reply ? "Check wiring and pull-ups" :
                busy ? "Another tool is using it" :
                firmware_missing ? "Timed I2C API required" :
                failed ? "Check bus and retry" :
                cancelled ? "Press OK to scan" : "Press OK to scan";
            const char* short_title = no_reply ? "No devices" :
                firmware_missing ? "Firmware error" : title;
            const char* short_explanation = no_reply ? "Wiring / pull-ups" :
                busy ? "Tool owns the bus" :
                firmware_missing ? "Timed API required" :
                failed ? "Check bus / retry" : explanation;
            canvas_set_font(canvas, FontPrimary);
            uint16_t width = canvas_string_width(canvas, title);
            if(width > 112U) {
                canvas_set_font(canvas, FontSecondary);
                width = canvas_string_width(canvas, title);
            }
            if(width > 112U) {
                title = short_title;
                canvas_set_font(canvas, FontPrimary);
                width = canvas_string_width(canvas, title);
            }
            if(width <= 112U)
                canvas_draw_str(canvas, (128U-width)/2U, 34U, title);

            canvas_set_font(canvas, FontSecondary);
            width = canvas_string_width(canvas, explanation);
            if(width > 112U) {
                explanation = short_explanation;
                width = canvas_string_width(canvas, explanation);
            }
            if(width <= 112U)
                canvas_draw_str(canvas, (128U-width)/2U, 43U, explanation);
        }
        canvas_set_font(canvas, FontSecondary);
        if(status == LabMateI2cRuntimeReady || scanning) {
            const char* msg = scanning ? "Scanning bus..." : "Press OK to scan";
            const uint16_t text_width = canvas_string_width(canvas, msg);
            if(text_width <= 120U)
                canvas_draw_str(canvas, (128U-text_width)/2U, 53U, msg);
        }
    }

    (void)ui_kit_key_hint(canvas, 4U, UiKitKeyOk,
                          scanning ? "Stop" : (found || no_reply) ?
                          "Scan again" : "Scan");
    /* The actual input handler changes I2C pages on UP/DOWN, not LR.
     * Do not present a false control: show the chip for real multipage
     * results only, with UP/DOWN's existing glyph. */
    if(found && result.page_count > 1U)
        (void)ui_kit_key_hint(canvas, 70U, UiKitKeyUpDown, "Page");
    canvas_set_color(canvas, ColorBlack);
}
