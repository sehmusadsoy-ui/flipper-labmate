#include "labmate_ui_screens.h"
#include "labmate_ui_primitives.h"
#include "labmate_ui_status.h"
#include "labmate_counter_math.h"
#include "labmate_generator.h"

#include <stdio.h>
#include <string.h>

/* Passive UI renderers only: app state is read under the UI mutex.
 * No SD, IRQ, GPIO or timer access in this module.
 */

/* Profile storage only runs in app thread; this renderer is read-only. */
void draw_profiles(Canvas* canvas, LabMateApp* app) {
    /* Always identify the selected operation, even when a status badge
     * (PWM ON, SAVED, etc.) temporarily replaces the top-right label. */
    const char* action = app->profile_action == 0U ? "LOAD" :
                         app->profile_action == 1U ? "SAVE" : "DELETE";
    const bool blocked = app->generator_running ||
                         app->capture_owner != LabMateCaptureNone ||
                         app->logger_recording;
    const char* state = action;
    if(app->profile_busy) state = "WAIT";
    else if(app->profile_io == LabMateProfileIoCorrupt) state = "CRC";
    else if(app->profile_io == LabMateProfileIoError) state = "SD ERR";
    else if(app->generator_running) state = "PWM ON";
    else if(app->capture_owner != LabMateCaptureNone || app->logger_recording)
        state = "BUSY";
    else if(app->profile_notice == 1U) state = "SAVED";
    else if(app->profile_notice == 2U) state = "LOADED";
    else if(app->profile_notice == 3U) state = "EMPTY";
    else if(app->profile_notice == 4U) state = "PWM ON";
    else if(app->profile_notice == 5U) state = "ERR";
    else if(app->profile_notice == 6U) state = "DELETED";
    else if(app->profile_notice == 7U) state = "PRESET";
    else if(app->profile_notice == 8U) state = "BUSY";

    ui_draw_header(canvas, "PROFILES");
    ui_badge(canvas, 77, 1, 49, state, false);
    canvas_set_font(canvas, FontSecondary);

    if(!app->profile_busy && app->profile_confirm) {
        /* A dedicated confirmation screen prevents a highlighted slot from
         * being mistaken for a harmless action selector. */
        const uint8_t slot_id = app->profile_selected + 1U;
        const bool deleting = app->profile_action == 2U;
        const bool overwrite = app->profiles.slots[app->profile_selected].present;
        char question[24];
        if(deleting) {
            snprintf(question, sizeof(question), "DELETE S%u?", (unsigned)slot_id);
        } else if(overwrite) {
            snprintf(question, sizeof(question), "OVERWRITE S%u?", (unsigned)slot_id);
        } else {
            snprintf(question, sizeof(question), "SAVE TO S%u?", (unsigned)slot_id);
        }
        canvas_draw_str(canvas, 5, 29, question);
        canvas_draw_str(canvas, 5, 43, deleting ? "CANNOT UNDO" :
                        (overwrite ? "REPLACES SAVED DATA" : "NEW PROFILE"));
        ui_footer_pair(canvas, "OK",
                       app->profile_action == 2U ? "DELETE" : "SAVE",
                       "BACK", "NO");
        return;
    }

    /* One readable row per legacy CRC-protected slot. */
    for(uint8_t i = 0U; i < LABMATE_PROFILE_SLOT_COUNT; ++i) {
        const uint8_t y = (uint8_t)(24U + 12U * i);
        const bool selected = app->profile_selected == i;
        if(selected) {
            canvas_draw_box(canvas, 1, y - 9, 126, 11);
            canvas_set_color(canvas, ColorWhite);
        }
        char slot_id[5];
        char summary[22];
        snprintf(slot_id, sizeof(slot_id), "S%u", (unsigned)(i + 1U));
        const LabMateProfile* slot = &app->profiles.slots[i];
        if(!slot->present) {
            snprintf(summary, sizeof(summary), "EMPTY");
        } else {
            const uint32_t freq = labmate_generator_frequencies[slot->generator_index];
            if(freq >= 1000U && freq % 1000U == 0U) {
                snprintf(summary, sizeof(summary), "%s / %lukHz",
                         slot->frequency_pin == 4U ? "PB3" : "PC1",
                         (unsigned long)(freq / 1000U));
            } else {
                snprintf(summary, sizeof(summary), "%s / %luHz",
                         slot->frequency_pin == 4U ? "PB3" : "PC1",
                         (unsigned long)freq);
            }
        }
        canvas_draw_str(canvas, 5, y, slot_id);
        canvas_draw_str_aligned(canvas, 122, y, AlignRight, AlignBottom, summary);
        if(selected) canvas_set_color(canvas, ColorBlack);
    }

    if(app->profile_busy) {
        canvas_draw_line(canvas, 0, 52, 127, 52);
        canvas_draw_str(canvas, 7, 62, "SD BUSY - WAIT");
    } else {
        /* Even under PWM ON, LR always names the operation and OK says
         * BLOCK. No hidden route to SAVE or DELETE under live PWM. */
        ui_footer_pair(canvas, "LR", action, "OK", blocked ? "BLOCK" : "SELECT");
    }
}

/* ABOUT quick guide: 0 overview, 1 repository, 2..12 one page per tool.
 * All strings are short enough for the 128x64 secondary 6px font.
 * Descriptions reflect actual capture pins, controls and limits.
 */
typedef struct {
    const char* purpose;
    const char* input;
    const char* method;
    const char* control;
} LabMateHelpPage;

static const LabMateHelpPage labmate_help[LabMateToolCount] = {
    [LabMateToolGpio] = {
        "GPIO MONITOR", "8 GPIO logic levels",
        "EDGES = poll changes", "<>PIN  OK HOLD",
    },
    [LabMateToolFrequency] = {
        "FREQUENCY METER", "PC1 LOW / PB3 HIGH",
        "Period / TIM2 count", "<> MODE  OK HOLD",
    },
    [LabMateToolPulse] = {
        "PULSE ANALYZER", "PC1 edges: rise/fall",
        "HIGH LOW PERIOD DUTY", "^ STATS  OK HOLD",
    },
    [LabMateToolGenerator] = {
        "PWM STUDIO", "PA7 TIM1 PWM / 3.3V",
        "1Hz-50kHz; duty 5-95", "<>Hz ^vDUTY OK RUN",
    },
    [LabMateToolLogger] = {
        "DATA LOGGER", "PC1/PB3 SD CSV",
        "1 second sampling", "<>SRC  OK REC/STOP",
    },
    [LabMateToolHistory] = {
        "LOG HISTORY", "Browse saved CSV",
        "Open or delete one", "UD FILE LR MODE OK",
    },
    [LabMateToolAbout] = {
        "ABOUT / GUIDE", "17 pages, 15 tools",
        "3.3V GPIO only", "<> PAGE  BK EXIT",
    },
    [LabMateToolProfiles] = {
        "PROFILES", "S1-S3 saved setups",
        "LOAD keeps PWM STOP", "<>ACTION OK SELECT",
    },
    [LabMateToolCounter] = {
        "EVENT COUNTER", "PB3 TIM2 rise count",
        "64-bit count / time", "OK RUN/STOP ^RESET",
    },
    [LabMateToolButton] = {
        "BUTTON ANALYZER", "PC1 LOW=press (PU)",
        "DB / BOUNCE / SETTLE", "OK RUN vDETAIL <>DB",
    },
    [LabMateToolAlerts] = {
        "THRESHOLD ALERTS", "FREQ DUTY CNT SETTLE",
        ">= limit latches", "<>SRC ^vLIM OK ARM",
    },
    [LabMateToolUart] = {
        "UART TERMINAL", "13 TX / 14 RX 3.3V",
        "9600-115200 8N1", "OK RUN DN EDIT TX",
    },
    [LabMateToolOneWire] = {
        "1-WIRE TEMP", "PA4 DQ / 3.3V VDD",
        "External sensor VDD", "OK READ  BK EXIT",
    },
    [LabMateToolI2c] = {
        "I2C EXPLORER", "PC0 SCL / PC1 SDA",
        "3.3V OWNED BUS", "OK SCAN BK EXIT",
    },
    [LabMateToolScope] = {
        "LOGIC SCOPE", "PC1 3.3V DIGITAL",
        "Measured edges only", "OK RUN/STOP BK EXIT",
    },
};

void draw_about(Canvas* canvas, LabMateApp* app) {
    const uint8_t total = (uint8_t)(LabMateToolCount + 2U);
    const uint8_t page = app->about_page < total ? app->about_page : 0U;
    char index[12];
    snprintf(index, sizeof(index), "%u/%u", (unsigned)(page + 1U), (unsigned)total);
    ui_draw_header(canvas, page == 0U ? "ABOUT" :
                           page == 1U ? "PROJECT" : "TOOL GUIDE");
    ui_badge(canvas, 91, 1, 35, index, false);
    canvas_set_font(canvas, FontSecondary);
    if(page == 0U) {
        canvas_draw_str(canvas, 3, 23, "LabMate " LABMATE_VERSION_TEXT);
        canvas_draw_str(canvas, 3, 33, "SauronLAB / Sehmus");
        canvas_draw_str(canvas, 3, 43, "15 tool guides");
        canvas_draw_str(canvas, 3, 51, "3.3V GPIO ONLY");
    } else if(page == 1U) {
        canvas_draw_str(canvas, 3, 23, "Source / releases:");
        canvas_draw_str(canvas, 3, 33, "github.com/");
        canvas_draw_str(canvas, 3, 43, "sehmusadsoy-ui/");
        canvas_draw_str(canvas, 3, 51, "flipper-labmate");
    } else {
        const LabMateHelpPage* help = &labmate_help[page - 2U];
        canvas_draw_str(canvas, 3, 23, help->purpose);
        canvas_draw_str(canvas, 3, 33, help->input);
        canvas_draw_str(canvas, 3, 43, help->method);
        canvas_draw_str(canvas, 3, 51, help->control);
    }
    canvas_draw_line(canvas, 0, 53, 127, 53);
    canvas_draw_str(canvas, 3, 62, "<> PAGE   BK MENU");
}

void draw_history(Canvas* canvas, LabMateApp* app) {
    char index[10] = "0/0";
    if(app->history_count > 0U) {
        snprintf(index, sizeof(index), "%u/%u",
                 (unsigned)(app->history_selected + 1U),
                 (unsigned)app->history_count);
    }
    ui_draw_header(canvas, "HISTORY");
    ui_badge(canvas, 91, 1, 35,
             app->history_busy ? "WAIT" :
             app->history_error ? "ERR" :
             app->history_delete_notice == 2U ? "FAIL" :
             app->history_delete_notice == 1U ? "DONE" : index, false);
    canvas_set_font(canvas, FontSecondary);

    if(app->history_delete_confirm &&
       app->history_selected < app->history_count) {
        char file[20];
        snprintf(file, sizeof(file), "log_%04u.csv",
                 (unsigned)app->history_ids[app->history_selected]);
        /* Explicit two-step, single-file confirmation. */
        canvas_draw_str(canvas, 3, 23, "DELETE THIS FILE?");
        canvas_draw_str(canvas, 3, 35, file);
        canvas_draw_str(canvas, 3, 48, "CANNOT UNDO");
        ui_footer_pair(canvas, "OK", "DELETE", "BACK", "NO");
        return;
    }

    if(app->history_busy) {
        canvas_draw_str(canvas, 3, 36,
                        app->history_delete_mode ? "DELETING / SCANNING" :
                                                   "SCANNING SD...");
    } else if(app->history_error) {
        canvas_draw_str(canvas, 3, 36, "SD READ ERROR");
    } else if(app->history_count == 0U) {
        canvas_draw_str(canvas, 3, 36, "NO SAVED LOGS");
    } else {
        const uint8_t first = (uint8_t)((app->history_selected / 3U) * 3U);
        for(uint8_t row = 0U; row < 3U; ++row) {
            const uint8_t idx = (uint8_t)(first + row);
            if(idx >= app->history_count) break;
            const uint8_t y = (uint8_t)(24U + row * 12U);
            const bool selected = idx == app->history_selected;
            if(selected) {
                canvas_draw_box(canvas, 1, y - 9, 126, 11);
                canvas_set_color(canvas, ColorWhite);
            }
            char number[5];
            char filename[22];
            snprintf(number, sizeof(number), "%02u", (unsigned)(idx + 1U));
            snprintf(filename, sizeof(filename), "log_%04u.csv",
                     (unsigned)app->history_ids[idx]);
            canvas_draw_str(canvas, 5, y, number);
            canvas_draw_str_aligned(canvas, 122, y, AlignRight, AlignBottom, filename);
            if(selected) canvas_set_color(canvas, ColorBlack);
        }
    }
    if(app->history_busy || app->history_error || app->history_count == 0U) {
        canvas_draw_line(canvas, 0, 52, 127, 52);
        canvas_draw_str(canvas, 6, 62, "BACK: MENU");
    } else {
        /* LEFT/RIGHT toggles action; OK previews or asks to delete. */
        ui_footer_pair(canvas, "LR", "MODE", "OK",
                       app->history_delete_mode ? "DELETE" : "OPEN");
    }
}

void draw_history_detail(Canvas* canvas, LabMateApp* app) {
    const bool has_file = app->history_selected < app->history_count;
    const char* state = app->history_busy ? "WAIT" :
                        app->history_error ? "ERR" :
                        app->history_loading ? "READ" : "CSV";

    ui_draw_header(canvas, "LOG VIEW");
    ui_badge(canvas, 91, 1, 35, state, false);
    canvas_set_font(canvas, FontSecondary);

    if(!has_file) {
        canvas_draw_str(canvas, 3, 35, "NO LOG SELECTED");
    } else {
        char value[32];
        snprintf(value, sizeof(value), "log_%04u.csv",
                 (unsigned)app->history_ids[app->history_selected]);
        canvas_draw_str(canvas, 3, 22, "FILE");
        canvas_draw_str_aligned(canvas, 125, 22, AlignRight, AlignBottom, value);
        canvas_draw_line(canvas, 2, 25, 125, 25);

        if(app->history_busy || app->history_error) {
            canvas_draw_str(canvas, 3, 39, app->history_busy ?
                            "OPENING SD..." : "SD READ ERROR");
        } else {
            const char* mode = "UNKNOWN";
            if(app->history_mode == 1U) mode = "FREQ / PC1";
            else if(app->history_mode == 2U) mode = "FREQ / PB3";
            else if(app->history_mode == 3U) mode = "PULSE / PC1";
            canvas_draw_str(canvas, 3, 34, "MODE");
            canvas_draw_str_aligned(canvas, 125, 34, AlignRight, AlignBottom, mode);
            snprintf(value, sizeof(value), "%lu", (unsigned long)app->history_rows);
            canvas_draw_str(canvas, 3, 43,
                            app->history_loading ? "READ ROWS" : "ROWS");
            canvas_draw_str_aligned(canvas, 125, 43, AlignRight, AlignBottom, value);
            snprintf(value, sizeof(value), "%lu s",
                     (unsigned long)(app->history_last_ms / 1000U));
            canvas_draw_str(canvas, 3, 51, "TIME");
            canvas_draw_str_aligned(canvas, 125, 51, AlignRight, AlignBottom, value);
        }
    }
    canvas_draw_line(canvas, 0, 52, 127, 52);
    canvas_draw_str(canvas, 6, 62, "BACK: LIST");
    canvas_draw_str_aligned(canvas, 125, 62, AlignRight, AlignBottom, "READ ONLY");
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
    ui_badge(canvas, 70, 1, 56, LABMATE_VERSION_TEXT, false);
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
    ui_badge(canvas, 91, 1, 35,
             labmate_ui_status_label(labmate_ui_gpio_monitor_status(
                 app->monitor_release_fault, app->monitor_blocked, app->hold)),
             !app->hold && !app->monitor_blocked);

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

    /* Use the shared two-column footer to keep tool key labels aligned. */
    ui_footer_pair(canvas, "<>", "PIN", "OK", app->hold ? "LIVE" : "HOLD");
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
             app->threshold.armed && app->threshold.latched &&
                     app->threshold.source == LabMateAlertFrequency ?
                 "ALRT" : app->capture_blocked ? "ERR" :
                 (app->hold ? "HOLD" : "LIVE"),
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

    /* Three identical action slots across measurement main screens. */
    ui_footer_triple(canvas, "<> MODE", app->hold ? "OK LIVE" : "OK HOLD", "^RST");
}

/* Threshold configuration is read-only from the Canvas callback.
 * Monitoring and latch transitions occur in the application thread.
 */
void draw_alerts(Canvas* canvas, LabMateApp* app) {
    char limit[32];
    const bool latched = app->threshold.armed && app->threshold.latched;
    ui_draw_header(canvas, "THRESHOLDS");
    ui_badge(canvas, 92, 1, 35,
             latched ? "ALRT" : app->threshold.armed ? "ARM" : "OFF",
             app->threshold.armed);

    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 3, 23, "SOURCE");
    canvas_draw_str_aligned(
        canvas, 125, 23, AlignRight, AlignBottom,
        labmate_threshold_source_name(app->threshold.source));
    canvas_draw_line(canvas, 2, 26, 125, 26);
    canvas_draw_str(canvas, 3, 35, "LIMIT");
    snprintf(limit, sizeof(limit), "%lu %s",
             (unsigned long)app->threshold.limit,
             labmate_threshold_source_unit(app->threshold.source));
    canvas_draw_str_aligned(canvas, 125, 35, AlignRight, AlignBottom, limit);

    /* State text never includes key combinations or cryptic arrows.
     * ACK is advertised in the footer only when there is an actual latch.
     */
    const char* state_text = !app->threshold.armed ? "DISARMED" :
                             latched ? "ALERT LATCHED" :
                             !app->threshold.has_sample ? "WAITING FOR INPUT" :
                             app->threshold.active ? "LIMIT REACHED" : "BELOW LIMIT";
    canvas_draw_frame(canvas, 2, 39, 124, 12);
    canvas_draw_str(canvas, 6, 48, state_text);

    if(!app->threshold.armed) {
        ui_footer_pair(canvas, "LR", "SOURCE", "OK", "ARM");
    } else if(latched) {
        ui_footer_pair(canvas, "DOWN", "ACK", "OK", "OFF");
    } else {
        ui_footer_pair(canvas, "OK", "OFF", "BACK", "EXIT");
    }
}

/* Button Analyzer shows contact bounce and first-edge-to-stable latency.
 * This renderer reads only the app-thread published snapshot.
 */
void draw_button(Canvas* canvas, LabMateApp* app) {
    char value[32];
    const bool alert = app->threshold.armed && app->threshold.latched &&
                       app->threshold.source == LabMateAlertButtonSettle;
    ui_draw_header(canvas, "BUTTON");
    ui_badge(canvas, 92, 1, 34,
             alert ? "ALRT" : app->capture_blocked ? "BUSY" :
             app->button_active ? "RUN" : "STOP", app->button_active);

    canvas_set_font(canvas, FontSecondary);
    if(!app->button_details_view) {
        /* Source and debounce remain on their own line. */
        canvas_draw_str(canvas, 3, 22, "PC1 / PULLUP");
        snprintf(value, sizeof(value), "DB %u ms",
                 (unsigned)app->button_quiet_ms);
        canvas_draw_str_aligned(canvas, 125, 22, AlignRight, AlignBottom, value);

        /* Simple status row avoids crowding text inside a narrow frame.
         * A single divider separates contact state from measurements. */
        canvas_draw_str(canvas, 3, 31, "CONTACT");
        canvas_draw_str_aligned(canvas, 125, 31, AlignRight, AlignBottom,
                                app->button_stats.pending ? "SETTLING" :
                                app->button_stats.stable_level ? "OPEN" : "CLOSED");
        canvas_draw_line(canvas, 2, 34, 125, 34);
        canvas_draw_line(canvas, 63, 36, 63, 51);
        canvas_draw_str(canvas, 3, 42, "PRESSES");
        canvas_draw_str(canvas, 67, 42, "RELEASES");
        snprintf(value, sizeof(value), "%lu",
                 (unsigned long)app->button_stats.presses);
        canvas_draw_str(canvas, 3, 51, value);
        snprintf(value, sizeof(value), "%lu",
                 (unsigned long)app->button_stats.releases);
        canvas_draw_str(canvas, 67, 51, value);
    } else {
        /* Dense data is split into a 2x2 grid with separate labels. */
        canvas_draw_line(canvas, 63, 17, 63, 51);
        canvas_draw_line(canvas, 2, 33, 125, 33);
        canvas_draw_str(canvas, 3, 22, "BOUNCE us");
        canvas_draw_str(canvas, 67, 22, "SETTLE ms");
        snprintf(value, sizeof(value), "%lu",
                 (unsigned long)app->button_bounce_us);
        canvas_draw_str(canvas, 3, 31, value);
        snprintf(value, sizeof(value), "%lu",
                 (unsigned long)app->button_settle_ms);
        canvas_draw_str(canvas, 67, 31, value);

        canvas_draw_str(canvas, 3, 42, "HOLD ms");
        canvas_draw_str(canvas, 67, 42, "BOUNCE N");
        snprintf(value, sizeof(value), "%lu",
                 (unsigned long)app->button_hold_ms);
        canvas_draw_str(canvas, 3, 51, value);
        snprintf(value, sizeof(value), "%u",
                 (unsigned)app->button_stats.last_bounce_edges);
        canvas_draw_str(canvas, 67, 51, value);
    }

    const char* button_action = app->button_active ? "STOP" :
        (app->button_session_started ? "RESUME" : "START");
    if(app->button_details_view) {
        ui_footer_pair(canvas, "DOWN", "MAIN", "OK", button_action);
    } else {
        ui_footer_pair(canvas, "DOWN", "MORE", "OK", button_action);
    }
}

/* Event Counter is a passive 64-bit display of PB3/TIM2 rising edges.
 * No hardware or timer access is performed from a Canvas callback.
 */
void draw_counter(Canvas* canvas, LabMateApp* app) {
    char count[24];
    char time_text[16];
    if(!labmate_counter_format(app->counter_total, count, sizeof(count))) {
        snprintf(count, sizeof(count), "COUNT ERROR");
    }
    const uint32_t seconds = app->counter_elapsed_seconds;
    if(seconds < 60U) {
        snprintf(time_text, sizeof(time_text), "%lu s", (unsigned long)seconds);
    } else if(seconds < 3600U) {
        snprintf(time_text, sizeof(time_text), "%lu:%02lu",
                 (unsigned long)(seconds / 60U),
                 (unsigned long)(seconds % 60U));
    } else if(seconds < 360000U) {
        snprintf(time_text, sizeof(time_text), "%luh%02lum",
                 (unsigned long)(seconds / 3600U),
                 (unsigned long)((seconds / 60U) % 60U));
    } else {
        snprintf(time_text, sizeof(time_text), ">99h");
    }

    ui_draw_header(canvas, "COUNTER");
    ui_badge(canvas, 92, 1, 34,
             app->threshold.armed && app->threshold.latched &&
                     app->threshold.source == LabMateAlertCounter ?
                 "ALRT" : app->capture_blocked ? "BUSY" :
                 app->counter_active ? "RUN" : "STOP",
             app->counter_active);

    /* Deliberate hierarchy: input source, then two BALANCED readouts.
     * Elapsed time is not buried in a tiny suffix above the large count.
     * For giant 64-bit counts, display the entire decimal value instead
     * of truncating or allowing it to run into the time column.
     */
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 3, 22, "PB3 / TIM2 / RISE");

    const size_t count_len = strlen(count);
    if(count_len > 11U) {
        canvas_draw_line(canvas, 2, 26, 125, 26);
        canvas_draw_str(canvas, 3, 35, "TOTAL COUNT");
        canvas_draw_str_aligned(canvas, 125, 35, AlignRight, AlignBottom, time_text);
        canvas_set_font(canvas, FontSecondary);
        canvas_draw_str(canvas, 3, 49, count);
    } else {
        canvas_draw_line(canvas, 80, 27, 80, 51);
        canvas_draw_str(canvas, 4, 34, "COUNT");
        canvas_draw_str(canvas, 86, 34, "TIME");
        canvas_set_font(canvas, count_len <= 7U ? FontPrimary : FontSecondary);
        canvas_draw_str(canvas, 4, 49, count);
        canvas_set_font(canvas, strlen(time_text) <= 4U ? FontPrimary : FontSecondary);
        canvas_draw_str_aligned(canvas, 106, 49, AlignCenter, AlignBottom, time_text);
    }

    if(app->counter_active) {
        ui_footer_pair(canvas, "OK", "STOP", "BACK", "EXIT");
    } else {
        const bool paused = app->counter_total != 0U || app->counter_elapsed_ticks != 0U;
        ui_footer_pair(canvas, "OK", paused ? "RESUME" : "START", "UP", "RESET");
    }
}

/* Display-only PWM Studio renderer. No TIM1 / GPIO writes here. */
void draw_generator(Canvas* canvas, LabMateApp* app) {
    char value[24];
    char duty[12];
    char step[24];
    const uint32_t freq = labmate_generator_frequency(app);

    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 2, 10, "PWM");
    ui_badge(canvas, 34, 1, 55, "OUT PA7", false);
    ui_badge(canvas, 91, 1, 35,
             app->generator_release_fault ? "ERR" :
                 app->generator_blocked ? "BUSY" :
                     app->generator_running ? "RUN" : "STOP",
             app->generator_running && !app->generator_blocked);
    canvas_draw_line(canvas, 0, 13, 127, 13);

    if(freq >= 1000U && (freq % 1000U) == 0U) {
        snprintf(value, sizeof(value), "%lu kHz", (unsigned long)(freq / 1000U));
    } else {
        snprintf(value, sizeof(value), "%lu Hz", (unsigned long)freq);
    }
    snprintf(duty, sizeof(duty), "%u%%", (unsigned)app->generator_duty_percent);

    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 3, 24, app->generator_editing ? "EDIT CUSTOM" :
                    app->generator_freq_index == LABMATE_PWM_CUSTOM_INDEX ?
                        "CUSTOM FREQ" : "OUTPUT FREQ");
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 4, 40, value);
    canvas_draw_line(canvas, 84, 17, 84, 50);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 90, 27, "DUTY");
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 90, 41, duty);

    canvas_set_font(canvas, FontSecondary);
    if(app->generator_editing) {
        snprintf(step, sizeof(step), "STEP %lu",
                 (unsigned long)labmate_generator_custom_step_hz(app));
        canvas_draw_str(canvas, 3, 49, step);
        ui_footer_pair(canvas, "LR", "HZ", "OK", "SAVE");
    } else {
        canvas_draw_str(canvas, 3, 49, "UP DOWN: DUTY");
        if(app->generator_running) {
            ui_footer_pair(canvas, "OK", "STOP", "BACK", "MENU");
        } else {
            ui_footer_pair(canvas, "LR", "FREQ", "OK", "RUN");
        }
    }
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
             app->threshold.armed && app->threshold.latched &&
                     app->threshold.source == LabMateAlertPulseDuty ?
                 "ALRT" : app->capture_blocked ? "ERR" :
                 (app->hold ? "HOLD" : "LIVE"),
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

    /* Main view only. The dense STATS view retains its own y=62 captions. */
    ui_footer_triple(canvas, "<>PIN", app->hold ? "OK LIVE" : "OK HOLD", "^STAT");
}

/* Read-only Data Logger dashboard; all SD work stays in app loop. */
void draw_logger(Canvas* canvas, LabMateApp* app) {
    char mode[24];
    char live[32];
    char state[32];
    const char* badge = "READY";

    if(app->logger_source == LoggerPulse) {
        snprintf(mode, sizeof(mode), "PULSE / PC1");
        if(app->pulse_period_valid) {
            const uint64_t us = pulse_cycles_to_us(app->pulse_period_cycles);
            if(us < 1000ULL) {
                snprintf(live, sizeof(live), "%luus / %lu.%lu%%",
                         (unsigned long)us,
                         (unsigned long)(app->pulse_duty_permille / 10U),
                         (unsigned long)(app->pulse_duty_permille % 10U));
            } else if(us < 1000000ULL) {
                snprintf(live, sizeof(live), "%lums / %lu.%lu%%",
                         (unsigned long)((us + 500ULL) / 1000ULL),
                         (unsigned long)(app->pulse_duty_permille / 10U),
                         (unsigned long)(app->pulse_duty_permille % 10U));
            } else {
                snprintf(live, sizeof(live), "%lus / %lu.%lu%%",
                         (unsigned long)((us + 500000ULL) / 1000000ULL),
                         (unsigned long)(app->pulse_duty_permille / 10U),
                         (unsigned long)(app->pulse_duty_permille % 10U));
            }
        } else {
            snprintf(live, sizeof(live), "NO VALID PULSE");
        }
    } else {
        snprintf(mode, sizeof(mode), "%s",
                 app->logger_source == LoggerFrequencyHigh ?
                    "FREQ / PB3 HIGH" : "FREQ / PC1 LOW");
        if(app->frequency_valid) {
            const uint32_t mhz = app->frequency_millihz;
            if(mhz >= 1000000U) {
                snprintf(live, sizeof(live), "%lu.%03lukHz",
                         (unsigned long)(mhz / 1000000U),
                         (unsigned long)((mhz % 1000000U) / 1000U));
            } else {
                snprintf(live, sizeof(live), "%lu.%03luHz",
                         (unsigned long)(mhz / 1000U),
                         (unsigned long)(mhz % 1000U));
            }
        } else {
            snprintf(live, sizeof(live), "NO VALID FREQ");
        }
    }

    if(app->logger_busy) {
        badge = "WAIT";
        snprintf(state, sizeof(state), "%s",
                 app->logger_busy_stopping ? "SAVING TO SD" : "OPENING SD");
    } else if(app->capture_blocked) {
        badge = "BUSY";
        snprintf(state, sizeof(state), "CAPTURE BLOCKED");
    } else if(app->logger_error) {
        badge = "ERR";
        snprintf(state, sizeof(state), "SD WRITE ERROR");
    } else if(app->logger_recording) {
        badge = "REC";
        snprintf(state, sizeof(state), "REC %lu ROWS",
                 (unsigned long)app->logger_rows);
    } else if(app->logger_path[0]) {
        badge = "DONE";
        snprintf(state, sizeof(state), "SAVED %lu",
                 (unsigned long)app->logger_rows);
    } else {
        snprintf(state, sizeof(state), "READY / 1 SEC SAMPLE");
    }

    ui_draw_header(canvas, "LOGGER");
    ui_badge(canvas, 91, 1, 35, badge, app->logger_recording);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 3, 22, "MODE");
    canvas_draw_str_aligned(canvas, 125, 22, AlignRight, AlignBottom, mode);
    canvas_draw_line(canvas, 2, 25, 125, 25);
    canvas_draw_str(canvas, 3, 35, "LIVE");
    canvas_draw_str_aligned(canvas, 125, 35, AlignRight, AlignBottom, live);
    canvas_draw_str(canvas, 3, 48, state);

    if(app->logger_busy) {
        canvas_draw_line(canvas, 0, 52, 127, 52);
        canvas_draw_str(canvas, 7, 62, "SD BUSY - WAIT");
    } else if(app->logger_recording) {
        ui_footer_pair(canvas, "OK", "STOP", "BACK", "SAVE");
    } else {
        ui_footer_pair(canvas, "LR", "SOURCE", "OK", "RECORD");
    }
}


