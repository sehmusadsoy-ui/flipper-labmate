#include "labmate_ui_screens.h"
#include "labmate_ui_primitives.h"

#include <stdio.h>

/* Passive UI renderers only: app state is read under the UI mutex.
 * No SD, IRQ, GPIO or timer access in this module.
 */

void draw_about(
    Canvas* canvas) {

    canvas_set_font(
        canvas,
        FontPrimary);

    canvas_draw_str(
        canvas,
        2,
        10,
        "LABMATE " LABMATE_VERSION_TEXT);

    canvas_draw_line(
        canvas,
        0,
        13,
        127,
        13);

    canvas_set_font(
        canvas,
        FontSecondary);

    canvas_draw_str(
        canvas,
        2,
        24,
        "Digital Signal Toolkit");

    canvas_draw_str(
        canvas,
        2,
        36,
        "LOW PC1");

    canvas_draw_str(
        canvas,
        47,
        36,
        "HIGH PB3");

    canvas_draw_str(
        canvas,
        2,
        48,
        "GEN PA7");

    canvas_draw_str(
        canvas,
        2,
        60,
        "3.3V GPIO ONLY");
}

void draw_history(Canvas* canvas, LabMateApp* app) {
    ui_draw_header(canvas, "LOG HISTORY");
    canvas_set_font(canvas, FontSecondary);
    if(app->history_busy) {
        canvas_draw_str(canvas, 2, 36, "SCANNING SD...");
    } else if(app->history_error) {
        canvas_draw_str(canvas, 2, 36, "SD / READ ERROR");
    } else if(app->history_count == 0U) {
        canvas_draw_str(canvas, 2, 36, "NO SAVED LOGS");
    } else {
        uint8_t first = (uint8_t)((app->history_selected / 3U) * 3U);
        for(uint8_t row = 0U; row < 3U; ++row) {
            uint8_t idx = (uint8_t)(first + row);
            if(idx >= app->history_count) break;
            char item[24];
            snprintf(
                item, sizeof(item), "%c log_%04u.csv",
                idx == app->history_selected ? '>' : ' ',
                (unsigned int)app->history_ids[idx]);
            canvas_draw_str(canvas, 2, (uint8_t)(24U + row * 12U), item);
        }
    }
    canvas_draw_str(canvas, 2, 61, "UP/DN  OK VIEW  BACK");
}

void draw_history_detail(Canvas* canvas, LabMateApp* app) {
    ui_draw_header(canvas, "LOG DETAIL");
    canvas_set_font(canvas, FontSecondary);
    if(app->history_selected >= app->history_count) {
        canvas_draw_str(canvas, 2, 36, "NO LOG SELECTED");
    } else {
        char line[36];
        snprintf(
            line, sizeof(line), "log_%04u.csv",
            (unsigned int)app->history_ids[app->history_selected]);
        canvas_draw_str(canvas, 2, 24, line);
        if(app->history_busy) {
            canvas_draw_str(canvas, 2, 36, "OPENING...");
        } else if(app->history_error) {
            canvas_draw_str(canvas, 2, 36, "SD / READ ERROR");
        } else {
            const char* mode = "EMPTY / UNKNOWN";
            if(app->history_mode == 1U) mode = "FREQ / PC1";
            else if(app->history_mode == 2U) mode = "FREQ / PB3";
            else if(app->history_mode == 3U) mode = "PULSE / PC1";
            canvas_draw_str(canvas, 2, 36, mode);
            snprintf(
                line, sizeof(line), "%s %lu  %lus",
                app->history_loading ? "READ" : "ROWS",
                (unsigned long)app->history_rows,
                (unsigned long)(app->history_last_ms / 1000U));
            canvas_draw_str(canvas, 2, 48, line);
        }
    }
    canvas_draw_str(canvas, 2, 61, "BACK LIST  READ ONLY");
}
