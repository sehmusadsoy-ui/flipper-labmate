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

/* Step 2: read-only renderers migrated verbatim from labmate.c. */
static const char* menu_items[MENU_COUNT] = {
    "GPIO Monitor",
    "Frequency Meter",
    "Pulse Analyzer",
    "Signal Generator",
    "Data Logger",
    "Log History",
    "About",
};

const char* const labmate_gpio_names[GPIO_COUNT] = {
    "PC0",
    "PC1",
    "PC3",
    "PB2",
    "PB3",
    "PA4",
    "PA6",
    "PA7",
};

void draw_menu(
    Canvas* canvas,
    LabMateApp* app) {

    /*
     * LabMate v1.2 instrument-style main menu.
     */

    canvas_set_font(
        canvas,
        FontPrimary);

    canvas_draw_str(
        canvas,
        2,
        10,
        "LABMATE");

    /*
     * Version badge.
     */
    ui_badge(
        canvas,
        99,
        1,
        27,
        LABMATE_VERSION_TEXT,
        false);

    canvas_draw_line(
        canvas,
        0,
        13,
        127,
        13);

    /*
     * Three visible rows.
     * Selected item remains centered where possible.
     */
    uint8_t first = 0;

    if(app->selected > 1) {
        first =
            app->selected - 1;
    }

    if(first + 3 > MENU_COUNT) {
        first =
            MENU_COUNT - 3;
    }

    for(uint8_t row = 0;
        row < 3;
        row++) {

        uint8_t i =
            first + row;

        uint8_t y =
            25 + (row * 12);

        if(i == app->selected) {

            /*
             * Inverted active row.
             */
            canvas_draw_box(
                canvas,
                1,
                y - 10,
                126,
                12);

            canvas_set_color(
                canvas,
                ColorWhite);

            ui_draw_menu_icon(
                canvas,
                i,
                4,
                y - 9);

            canvas_set_font(
                canvas,
                FontSecondary);

            canvas_draw_str(
                canvas,
                20,
                y,
                menu_items[i]);

            canvas_draw_str(
                canvas,
                117,
                y,
                ">");

            canvas_set_color(
                canvas,
                ColorBlack);

        } else {

            ui_draw_menu_icon(
                canvas,
                i,
                4,
                y - 9);

            canvas_set_font(
                canvas,
                FontSecondary);

            canvas_draw_str(
                canvas,
                20,
                y,
                menu_items[i]);

            canvas_draw_str(
                canvas,
                117,
                y,
                ">");
        }
    }

    canvas_draw_line(
        canvas,
        0,
        52,
        127,
        52);

    /*
     * Instrument-style navigation footer.
     */
    ui_key(
        canvas,
        2,
        "^v",
        "MOVE");

    ui_key(
        canvas,
        70,
        "OK",
        "OPEN");
}

void draw_gpio(Canvas* canvas, LabMateApp* app) {
    char edges_text[32];
    const uint32_t edges = app->edges;

    /* Compact instrument header, consistent with Frequency and Pulse screens. */
    ui_draw_header(canvas, "GPIO");
    ui_badge(canvas, 35, 1, 34, labmate_gpio_names[app->gpio_index], false);
    ui_badge(canvas, 91, 1, 35, app->hold ? "HOLD" : "LIVE", !app->hold);

    /* Separate the live logic level from the transition counter. */
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 4, 24, "LEVEL");
    canvas_draw_str(canvas, 70, 24, "EDGES");
    canvas_draw_line(canvas, 64, 18, 64, 50);

    /* Invert the level field only when HIGH; LOW remains outlined. */
    if(app->gpio_state) {
        canvas_draw_box(canvas, 2, 28, 58, 22);
        canvas_set_color(canvas, ColorWhite);
    } else {
        canvas_draw_frame(canvas, 2, 28, 58, 22);
    }
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, app->gpio_state ? 16 : 20, 44,
                    app->gpio_state ? "HIGH" : "LOW");
    if(app->gpio_state) canvas_set_color(canvas, ColorBlack);

    /* Keep large edge counts inside the 58-pixel value column. */
    if(edges >= 1000000U) {
        snprintf(edges_text, sizeof(edges_text), "%lu.%luM",
                 (unsigned long)(edges / 1000000U),
                 (unsigned long)((edges % 1000000U) / 100000U));
    } else if(edges >= 10000U) {
        snprintf(edges_text, sizeof(edges_text), "%lu.%luk",
                 (unsigned long)(edges / 1000U),
                 (unsigned long)((edges % 1000U) / 100U));
    } else {
        snprintf(edges_text, sizeof(edges_text), "%lu", (unsigned long)edges);
    }
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 70, 41, edges_text);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 70, 49, "POLL");

    canvas_draw_line(canvas, 0, 52, 127, 52);
    ui_key(canvas, 2, "<>", "PIN");
    ui_key(canvas, 70, "OK", app->hold ? "LIVE" : "HOLD");
}

/* Compact MIN/MAX display in two fixed-width cells.
 * Use the SAME truncation policy as the main frequency reading:
 * e.g. an actual 49.996 kHz displays as 49.99 kHz above and 49.99k
 * in MIN/MAX, rather than incorrectly appearing as 50.00k below.
 * Never switch units before the true 1 kHz / 10 kHz / 100 kHz boundary.
 * The stored millihertz measurements and recording logic are unchanged.
 */
static void frequency_format_compact(char* text, size_t size, uint32_t mhz, bool valid) {
    if(!valid) {
        snprintf(text, size, "---");
        return;
    }

    if(mhz >= 1000000000U) {
        /* 1.00 MHz and above. */
        uint32_t v = mhz / 10000000U;
        snprintf(text, size, "%lu.%02luM", (unsigned long)(v / 100U),
                 (unsigned long)(v % 100U));
    } else if(mhz >= 100000000U) {
        /* 100.0 kHz .. 999.9 kHz. */
        uint32_t v = mhz / 100000U;
        snprintf(text, size, "%lu.%01luk", (unsigned long)(v / 10U),
                 (unsigned long)(v % 10U));
    } else if(mhz >= 10000000U) {
        /* 10.00 kHz .. 99.99 kHz: same 10 Hz steps as the main reading. */
        uint32_t v = mhz / 10000U;
        snprintf(text, size, "%lu.%02luk", (unsigned long)(v / 100U),
                 (unsigned long)(v % 100U));
    } else if(mhz >= 1000000U) {
        /* 1.000 kHz .. 9.999 kHz. */
        uint32_t v = mhz / 1000U;
        snprintf(text, size, "%lu.%03luk", (unsigned long)(v / 1000U),
                 (unsigned long)(v % 1000U));
    } else if(mhz >= 10000U) {
        /* 10.0 .. 999.9 Hz; never round 999.9 Hz up to 1 kHz. */
        uint32_t v = mhz / 100U;
        snprintf(text, size, "%lu.%01luHz", (unsigned long)(v / 10U),
                 (unsigned long)(v % 10U));
    } else {
        /* 0.00 .. 9.99 Hz. */
        uint32_t v = mhz / 10U;
        snprintf(text, size, "%lu.%02luHz", (unsigned long)(v / 100U),
                 (unsigned long)(v % 100U));
    }
}

/* Edge count is intentionally abbreviated to retain an on-screen indicator. */
static void frequency_format_edges(char* text, size_t size, uint32_t edges) {
    if(edges >= 1000000U) {
        snprintf(text, size, "E:%luM", (unsigned long)(edges / 1000000U));
    } else if(edges >= 10000U) {
        snprintf(text, size, "E:%luk", (unsigned long)(edges / 1000U));
    } else {
        snprintf(text, size, "E:%lu", (unsigned long)edges);
    }
}

void draw_frequency(Canvas* canvas, LabMateApp* app) {
    char value[32];
    char edges_label[20];
    char min_value[20];
    char max_value[20];
    const bool high_mode = app->gpio_index == 4U;

    /* Compact status bar, matching the Pulse Analyzer layout. */
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 2, 10, "FREQ");
    ui_badge(canvas, 34, 1, 55, high_mode ? "HIGH PB3" : "LOW PC1", false);
    ui_badge(canvas, 91, 1, 35, app->hold ? "HOLD" : "LIVE", !app->hold);
    canvas_draw_line(canvas, 0, 13, 127, 13);

    if(app->frequency_valid) {
        uint32_t hz = app->frequency_millihz / 1000U;
        uint32_t decimal = (app->frequency_millihz % 1000U) / 10U;

        if(hz >= 1000U) {
            /* Keep the existing measured frequency formatting unchanged. */
            uint32_t khz_whole = hz / 1000U;
            uint32_t khz_decimal = (hz % 1000U) / 10U;
            snprintf(value, sizeof(value), "%lu.%02lu kHz",
                     (unsigned long)khz_whole,
                     (unsigned long)khz_decimal);
        } else {
            snprintf(value, sizeof(value), "%lu.%02lu Hz",
                     (unsigned long)hz,
                     (unsigned long)decimal);
        }
    } else {
        snprintf(value, sizeof(value), "--- Hz");
    }

    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 3, 24, "FREQUENCY");
    frequency_format_edges(edges_label, sizeof(edges_label), app->edges);
    canvas_draw_str(canvas, 83, 24, edges_label);

    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 4, 38, value);

    frequency_format_compact(min_value, sizeof(min_value),
        app->frequency_min_millihz, app->frequency_stats_valid);
    frequency_format_compact(max_value, sizeof(max_value),
        app->frequency_max_millihz, app->frequency_stats_valid);
    canvas_set_font(canvas, FontSecondary);
    /* Two fixed-width cells: MIN 0..64, MAX 66..127.
     * Seven 6px FontSecondary characters fit within each value area. */
    canvas_draw_str(canvas, 2, 49, "MIN");
    canvas_draw_str(canvas, 22, 49, min_value);
    canvas_draw_str(canvas, 66, 49, "MAX");
    /* Right-align the value to leave a readable gap after MAX without clipping. */
    canvas_draw_str_aligned(canvas, 127, 49, AlignRight, AlignBottom, max_value);

    /* Keep the three action hints separate at 128x64 resolution. */
    canvas_draw_line(canvas, 0, 52, 127, 52);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 2, 61, "<> MODE");
    canvas_draw_str(canvas, 49, 61, app->hold ? "OK LIVE" : "OK HOLD");
    canvas_draw_str(canvas, 102, 61, "^RST");
}

