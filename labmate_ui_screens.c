#include "labmate_ui_screens.h"
#include "labmate_ui_primitives.h"

#include <stdio.h>

/* Passive UI renderers only: app state is read under the UI mutex.
 * No SD, IRQ, GPIO or timer access in this module.
 */

/* Profile storage only runs in app thread; this renderer is read-only. */
void draw_profiles(Canvas* canvas, LabMateApp* app) {
    ui_draw_header(canvas, "PROFILES");
    canvas_set_font(canvas, FontSecondary);

    const char* state = "READY";
    if(app->profile_busy) state = "WAIT";
    else if(app->profile_io == LabMateProfileIoCorrupt) state = "BAD CRC";
    else if(app->profile_io == LabMateProfileIoError) state = "SD ERR";
    else if(app->profile_notice == 1U) state = "SAVED";
    else if(app->profile_notice == 2U) state = "LOADED";
    else if(app->profile_notice == 3U) state = "EMPTY";
    else if(app->profile_notice == 4U) state = "STOP PWM";
    else if(app->profile_notice == 5U) state = "WRITE ERR";
    else if(app->profile_notice == 6U) state = "DELETED";
    canvas_draw_str_aligned(canvas, 126, 10, AlignRight, AlignBottom, state);

    for(uint8_t i = 0U; i < LABMATE_PROFILE_SLOT_COUNT; ++i) {
        const uint8_t y = (uint8_t)(24U + 12U * i);
        if(app->profile_selected == i) {
            canvas_draw_box(canvas, 1, y - 10, 126, 12);
            canvas_set_color(canvas, ColorWhite);
        }
        char line[32];
        const LabMateProfile* slot = &app->profiles.slots[i];
        if(!slot->present) {
            snprintf(line, sizeof(line), "S%u  EMPTY", (unsigned)(i + 1U));
        } else {
            const uint32_t freq = labmate_generator_frequencies[slot->generator_index];
            if(freq >= 1000U && freq % 1000U == 0U) {
                snprintf(line, sizeof(line), "S%u %s %lukHz",
                         (unsigned)(i + 1U),
                         slot->frequency_pin == 4U ? "PB3" : "PC1",
                         (unsigned long)(freq / 1000U));
            } else {
                snprintf(line, sizeof(line), "S%u %s %luHz",
                         (unsigned)(i + 1U),
                         slot->frequency_pin == 4U ? "PB3" : "PC1",
                         (unsigned long)freq);
            }
        }
        canvas_draw_str(canvas, 5, y, line);
        if(app->profile_selected == i) canvas_set_color(canvas, ColorBlack);
    }

    canvas_draw_line(canvas, 0, 52, 127, 52);
    canvas_set_font(canvas, FontSecondary);
    if(app->profile_confirm) {
        canvas_draw_str(canvas, 2, 61, app->profile_action == 2U ?
                        "OK DELETE  BACK CANCEL" : "OK SAVE  BACK CANCEL");
    } else if(app->profile_busy) {
        canvas_draw_str(canvas, 2, 61, "SD: PLEASE WAIT");
    } else {
        const char* footer = app->profile_action == 0U ?
                             "<> LOAD   OK APPLY" :
                             app->profile_action == 1U ?
                             "<> SAVE   OK SELECT" :
                             "<> DELETE OK SELECT";
        canvas_draw_str(canvas, 2, 61, footer);
    }
}

void draw_about(Canvas* canvas) {
    /* Keep developer credit legible on the 128x64 monochrome display.
     * ASCII is deliberate: the standard Flipper font lacks Turkish glyphs.
     */
    ui_draw_header(canvas, "LABMATE " LABMATE_VERSION_TEXT);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 2, 24, "Digital Signal Toolkit");
    canvas_draw_line(canvas, 0, 29, 127, 29);
    canvas_draw_str(canvas, 2, 41, "DEV");
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 28, 42, "SauronLAB");
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 28, 52, "Sehmus");
    canvas_draw_str(canvas, 2, 62, "3.3V GPIO ONLY");
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
/* Menu labels and tool mapping now live in labmate_navigation.c. */

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

void draw_menu(Canvas* canvas, LabMateApp* app) {
    const bool inside = app->menu_in_group;
    const uint8_t count = inside ? labmate_nav_group_size(app->menu_group) :
                                  (uint8_t)LabMateGroupCount;
    const uint8_t selected = app->selected < count ? app->selected : 0U;

    /* The root lists categories; each child group lists its original tools.
     * No hardware state changes when navigating between menu levels.
     */
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 2, 10,
                    inside ? labmate_nav_group_title(app->menu_group) : "LABMATE");
    ui_badge(canvas, 80, 1, 48, LABMATE_VERSION_TEXT, false);
    canvas_draw_line(canvas, 0, 13, 127, 13);

    /* In three-item groups, always keep every row visible (no blank slot). */
    const uint8_t first = labmate_nav_first_visible(selected, count, 3U);
    for(uint8_t row = 0U; row < 3U && (uint8_t)(first + row) < count; ++row) {
        const uint8_t index = (uint8_t)(first + row);
        const uint8_t y = (uint8_t)(25U + row * 12U);
        const uint8_t tool = inside ?
            labmate_nav_tool_at(app->menu_group, index) :
            labmate_nav_group_icon(index);
        const char* title = inside ?
            labmate_nav_tool_title(tool) : labmate_nav_group_title(index);

        if(index == selected) {
            canvas_draw_box(canvas, 1, y - 10, 126, 12);
            canvas_set_color(canvas, ColorWhite);
        }
        ui_draw_menu_icon(canvas, tool, 4, y - 9);
        canvas_set_font(canvas, FontSecondary);
        canvas_draw_str(canvas, 20, y, title);
        canvas_draw_str(canvas, 117, y, ">");
        if(index == selected) canvas_set_color(canvas, ColorBlack);
    }

    canvas_draw_line(canvas, 0, 52, 127, 52);
    if(inside) {
        ui_key(canvas, 2, "BK", "ROOT");
        ui_key(canvas, 70, "OK", "OPEN");
    } else {
        ui_key(canvas, 2, "^v", "MOVE");
        ui_key(canvas, 70, "OK", "OPEN");
    }
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
    /* Background PWM retains PA7; display the reservation instead of
     * implying that all eight GPIO Monitor pins remain selectable.
     */
    canvas_draw_str(canvas, 70, 49, app->generator_running ? "PA7 BUSY" : "POLL");

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
    ui_badge(canvas, 91, 1, 35,
             app->capture_blocked ? "ERR" : (app->hold ? "HOLD" : "LIVE"),
             !app->hold);
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

/* Display-only Signal Generator renderer (TIM1 control remains in labmate.c). */
void draw_generator(Canvas* canvas, LabMateApp* app) {
    char value[32];
    const uint32_t freq = labmate_generator_frequencies[app->generator_freq_index];

    /* Output and RUN/STOP are visible even when switching presets. */
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 2, 10, "GEN");
    ui_badge(canvas, 34, 1, 55, "OUT PA7", false);
    ui_badge(canvas, 91, 1, 35, app->generator_running ? "RUN" : "STOP",
             app->generator_running);
    canvas_draw_line(canvas, 0, 13, 127, 13);

    /* Only the visual presentation changes: PWM remains TIM1/PA7. */
    if(freq >= 1000U && (freq % 1000U) == 0U) {
        snprintf(value, sizeof(value), "%lu kHz", (unsigned long)(freq / 1000U));
    } else {
        snprintf(value, sizeof(value), "%lu Hz", (unsigned long)freq);
    }

    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 3, 24, "OUTPUT FREQ");
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 4, 40, value);

    canvas_draw_line(canvas, 84, 17, 84, 50);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 90, 27, "DUTY");
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 90, 41, "50%");

    canvas_draw_line(canvas, 0, 52, 127, 52);
    ui_key(canvas, 2, "<>", "FREQ");
    ui_key(canvas, 70, "OK", app->generator_running ? "STOP" : "START");
}

/* Pulse screen formatters and Canvas renderers; measurements remain in app core. */
static void pulse_ui_format_value(char* text, size_t size, uint32_t cycles) {
    const uint64_t us = pulse_cycles_to_us(cycles);

    if(us < 1000ULL) {
        snprintf(text, size, "%luus", (unsigned long)us);
    } else if(us < 10000ULL) {
        snprintf(text, size, "%lu.%02lums",
                 (unsigned long)(us / 1000ULL),
                 (unsigned long)((us % 1000ULL) / 10ULL));
    } else if(us < 10000000ULL) {
        snprintf(text, size, "%lums", (unsigned long)((us + 500ULL) / 1000ULL));
    } else {
        snprintf(text, size, "%lus", (unsigned long)((us + 500000ULL) / 1000000ULL));
    }
}


static void pulse_ui_metric(
    Canvas* canvas,
    uint8_t x,
    uint8_t label_y,
    uint8_t value_y,
    const char* label,
    const char* value) {

    /* Both labels and values use the compact 6x8 font. The large
     * FontPrimary glyphs extend upwards into the label row inside
     * the LCD's 18-pixel metric cells, hiding parts of both strings. */
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, x, label_y, label);
    canvas_draw_str(canvas, x, value_y, value);
}

/* Second Pulse Analyzer page: four rows, MIN and MAX columns.
 * The 128x64 LCD cannot show twelve detailed values in the LIVE grid.
 * Keep the existing live 2x2 display untouched. */
static void draw_pulse_stats(Canvas* canvas, LabMateApp* app) {
    char hi_min[24] = "---";
    char hi_max[24] = "---";
    char lo_min[24] = "---";
    char lo_max[24] = "---";
    char per_min[24] = "---";
    char per_max[24] = "---";
    char duty_min[24] = "---";
    char duty_max[24] = "---";

    if(app->pulse_stats_valid) {
        pulse_ui_format_value(hi_min, sizeof(hi_min), app->pulse_min_high_cycles);
        pulse_ui_format_value(hi_max, sizeof(hi_max), app->pulse_max_high_cycles);
        pulse_ui_format_value(lo_min, sizeof(lo_min), app->pulse_min_low_cycles);
        pulse_ui_format_value(lo_max, sizeof(lo_max), app->pulse_max_low_cycles);
        pulse_ui_format_value(per_min, sizeof(per_min), app->pulse_min_period_cycles);
        pulse_ui_format_value(per_max, sizeof(per_max), app->pulse_max_period_cycles);
        snprintf(duty_min, sizeof(duty_min), "%lu.%lu%%",
                 (unsigned long)(app->pulse_min_duty_permille / 10U),
                 (unsigned long)(app->pulse_min_duty_permille % 10U));
        snprintf(duty_max, sizeof(duty_max), "%lu.%lu%%",
                 (unsigned long)(app->pulse_max_duty_permille / 10U),
                 (unsigned long)(app->pulse_max_duty_permille % 10U));
    }

    canvas_set_font(canvas, FontSecondary);
    /* Fixed table cells leave room for seven-character values in each
     * numeric column. The row baselines are >= 8px apart. */
    canvas_draw_str(canvas, 3, 20, "TYPE");
    canvas_draw_str(canvas, 42, 20, "MIN");
    canvas_draw_str(canvas, 87, 20, "MAX");
    canvas_draw_line(canvas, 0, 22, 127, 22);

    canvas_draw_str(canvas, 3, 30, "HIGH");
    canvas_draw_str(canvas, 40, 30, hi_min);
    canvas_draw_str(canvas, 85, 30, hi_max);

    canvas_draw_str(canvas, 3, 38, "LOW");
    canvas_draw_str(canvas, 40, 38, lo_min);
    canvas_draw_str(canvas, 85, 38, lo_max);

    canvas_draw_str(canvas, 3, 46, "PER");
    canvas_draw_str(canvas, 40, 46, per_min);
    canvas_draw_str(canvas, 85, 46, per_max);

    canvas_draw_str(canvas, 3, 54, "DUTY");
    canvas_draw_str(canvas, 40, 54, duty_min);
    canvas_draw_str(canvas, 85, 54, duty_max);

    /* Short footer labels fit across all 128 pixels; avoid text
     * beyond x=127 and a baseline on the bottommost pixel. */
    /* No rule over this footer: 8px letters start at y=55 while
     * the last measurement row ends at y=54. */
    canvas_draw_str(canvas, 3, 62, "vRST");
    canvas_draw_str(canvas, 45, 62, app->hold ? "OK LIVE" : "OK HOLD");
    canvas_draw_str(canvas, 95, 62, "^BACK");
}

void draw_pulse(Canvas* canvas, LabMateApp* app) {
    char high[24] = "---";
    char low[24] = "---";
    char period[24] = "---";
    char duty[24] = "---";

    /* Compact instrument header with input and capture state. */
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 2, 10, "PULSE");
    ui_badge(canvas, 56, 1, 33, labmate_gpio_names[app->gpio_index], false);
    ui_badge(canvas, 91, 1, 35,
             app->capture_blocked ? "ERR" : (app->hold ? "HOLD" : "LIVE"),
             !app->hold);
    canvas_draw_line(canvas, 0, 13, 127, 13);

    if(app->pulse_stats_view) {
        draw_pulse_stats(canvas, app);
        return;
    }

    if(app->pulse_high_valid) {
        pulse_ui_format_value(high, sizeof(high), app->pulse_high_cycles);
    }
    if(app->pulse_low_valid) {
        pulse_ui_format_value(low, sizeof(low), app->pulse_low_cycles);
    }
    if(app->pulse_period_valid) {
        pulse_ui_format_value(period, sizeof(period), app->pulse_period_cycles);
        snprintf(duty, sizeof(duty), "%lu.%lu%%",
                 (unsigned long)(app->pulse_duty_permille / 10U),
                 (unsigned long)(app->pulse_duty_permille % 10U));
    }

    /* 2 x 2 measurement grid.
     * Use separate baselines for text and separators: on the 128x64
     * display, even a one-pixel collision cuts the labels visibly.
     * The measurement values and IRQ engine are unchanged.
     */
    canvas_draw_line(canvas, 64, 15, 64, 51);
    canvas_draw_line(canvas, 2, 33, 126, 33);
    pulse_ui_metric(canvas, 3, 21, 31, "HIGH", high);
    pulse_ui_metric(canvas, 68, 21, 31, "LOW", low);
    pulse_ui_metric(canvas, 3, 41, 50, "PERIOD", period);
    pulse_ui_metric(canvas, 68, 41, 50, "DUTY", duty);

    /* Navigation: short captions fit the actual 128px viewport. */
    canvas_draw_line(canvas, 0, 52, 127, 52);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 3, 61, "<>PIN");
    canvas_draw_str(canvas, 45, 61, app->hold ? "OK LIVE" : "OK HOLD");
    canvas_draw_str(canvas, 96, 61, "^STAT");
}

/* Read-only Data Logger dashboard; all SD work stays in app loop. */
void draw_logger(Canvas* canvas, LabMateApp* app) {
    char mode[30];
    char live[40];
    char state[40];

    ui_draw_header(canvas, "DATA LOGGER");
    canvas_set_font(canvas, FontSecondary);
    if(app->logger_source == LoggerPulse) {
        snprintf(mode, sizeof(mode), "PULSE / PC1");
        if(app->pulse_period_valid) {
            snprintf(
                live, sizeof(live), "PER %lu us  DUTY %lu.%01lu%%",
                (unsigned long)pulse_cycles_to_us(app->pulse_period_cycles),
                (unsigned long)(app->pulse_duty_permille / 10U),
                (unsigned long)(app->pulse_duty_permille % 10U));
        } else {
            snprintf(live, sizeof(live), "NO VALID PULSE");
        }
    } else {
        snprintf(
            mode, sizeof(mode), "FREQ / %s",
            app->logger_source == LoggerFrequencyHigh ? "PB3 HIGH" : "PC1 LOW");
        if(app->frequency_valid) {
            snprintf(
                live, sizeof(live), "FREQ %lu.%03lu Hz",
                (unsigned long)(app->frequency_millihz / 1000U),
                (unsigned long)(app->frequency_millihz % 1000U));
        } else {
            snprintf(live, sizeof(live), "NO VALID FREQ");
        }
    }

    if(app->logger_busy) {
        snprintf(state, sizeof(state),
                 app->logger_busy_stopping ? "SAVING / WAIT" : "OPENING / WAIT");
    } else if(app->capture_blocked) {
        snprintf(state, sizeof(state), "CAPTURE BLOCKED");
    } else if(app->logger_error) {
        snprintf(state, sizeof(state), "SD / WRITE ERROR");
    } else if(app->logger_recording) {
        snprintf(state, sizeof(state), "REC: %lu rows", (unsigned long)app->logger_rows);
    } else if(app->logger_path[0]) {
        snprintf(state, sizeof(state), "SAVED: %lu rows", (unsigned long)app->logger_rows);
    } else {
        snprintf(state, sizeof(state), "READY / 1 second");
    }

    canvas_draw_str(canvas, 2, 24, mode);
    canvas_draw_str(canvas, 2, 36, live);
    canvas_draw_str(canvas, 2, 48, state);
    canvas_draw_str(
        canvas, 2, 61,
        app->logger_busy ? "PLEASE WAIT" :
        (app->logger_recording ? "OK STOP  BACK SAVE" : "< > MODE  OK REC"));
}


