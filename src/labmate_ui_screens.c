#include "labmate_ui_screens.h"
#include "labmate_ui_primitives.h"
#include "ui_kit.h"
#include "labmate_ui_status.h"
#include "labmate_counter_math.h"
#include "labmate_generator.h"
#include "labmate_info_ui.h"

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
            snprintf(question, sizeof(question), "Delete S%u?", (unsigned)slot_id);
        } else if(overwrite) {
            snprintf(question, sizeof(question), "Overwrite S%u?", (unsigned)slot_id);
        } else {
            snprintf(question, sizeof(question), "Save to S%u?", (unsigned)slot_id);
        }
        ui_kit_confirmation(canvas, question, "Confirm?", deleting ? "Delete" : "Save");
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

/* Original ABOUT guide strings, retained for Step 0/3 audit provenance.
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
        "ABOUT / GUIDE", "19 pages, 17 tools",
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
    [LabMateToolDoctor] = {
        "SIGNAL DOCTOR", "SEALED CAPTURE ONLY",
        "Ref by user, no guesses", "OK INFO or REF STEP",
    },
    [LabMateToolDashboard] = {
        "DASHBOARD", "FREQ/PULSE/SCOPE",
        "COUNT/LOGGER REVIEW", "UD SOURCE OK STATS",
    },
};

void draw_about(Canvas* canvas, LabMateApp* app) {
    /* This legacy source table is intentionally preserved for future
     * content audits; Step 3 no longer paints its ALL-CAPS help strings. */
    (void)labmate_help;
    if(app->info_section_motion) {
        const uint8_t frame = app->info_motion_frame;
        const bool outgoing = frame < 3U;
        const uint8_t section = outgoing ? app->info_previous_section : app->info_section;
        const int8_t slide = labmate_info_slide_pixel(frame, app->info_page_direction);
        const uint8_t fade = labmate_info_fade_strength(frame);
        switch(section) {
        case LabMateInfoHome:
            labmate_info_draw_home_motion(
                canvas, outgoing ? app->info_previous_home_selected : app->info_selected,
                app->ui_pulse_phase, slide, fade);
            return;
        case LabMateInfoGuideList:
            labmate_info_draw_guide_list_motion(
                canvas, app->info_guide_selected, slide, fade);
            return;
        case LabMateInfoGuideCard:
            labmate_info_draw_guide_card_motion(
                canvas, app->info_guide_selected,
                outgoing ? app->info_previous_scroll_px : 0, slide, fade);
            return;
        case LabMateInfoProject:
            labmate_info_draw_project_motion(canvas, slide, fade);
            return;
        case LabMateInfoSafety:
            labmate_info_draw_safety_motion(canvas, app->info_safety_page, slide, fade);
            return;
        default: break;
        }
    }
    switch(app->info_section) {
    case LabMateInfoHome:
        labmate_info_draw_home(canvas, app->info_selected, app->ui_pulse_phase);
        return;
    case LabMateInfoGuideList:
        labmate_info_draw_guide_list(canvas, app->info_guide_selected);
        return;
    case LabMateInfoGuideCard:
        if(app->info_page_motion) {
            const uint8_t frame = app->info_motion_frame;
            const bool outgoing = frame < 3U;
            labmate_info_draw_guide_card_motion(
                canvas,
                outgoing ? app->info_previous_guide : app->info_guide_selected,
                outgoing ? app->info_previous_scroll_px : 0,
                labmate_info_slide_pixel(frame, app->info_page_direction),
                labmate_info_fade_strength(frame));
        } else {
            labmate_info_draw_guide_card_motion(
                canvas, app->info_guide_selected, app->info_scroll_render_px,
                0, 0U);
        }
        return;
    case LabMateInfoProject:
        labmate_info_draw_project(canvas);
        return;
    case LabMateInfoSafety:
        labmate_info_draw_safety(canvas, app->info_safety_page);
        return;
    default:
        labmate_info_draw_home(canvas, 0U, app->ui_pulse_phase);
        return;
    }
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
        char question[28];
        snprintf(question, sizeof(question), "Delete log %u?",
                 (unsigned)app->history_ids[app->history_selected]);
        ui_kit_confirmation(canvas, question, "Delete log?", "Delete");
        return;
    }

    if(app->history_busy) {
        canvas_draw_str(canvas, 3, 36,
                        app->history_delete_mode ? "DELETING / SCANNING" :
                                                   "SCANNING SD...");
    } else if(app->history_error) {
        canvas_draw_str(canvas, 3, 36, "SD READ ERROR");
    } else if(app->history_count == 0U) {
        canvas_set_font(canvas, FontPrimary);
        ui_kit_center_text(canvas, 31, "No saved logs", NULL);
        ui_kit_pulse_line(canvas, 22, 40, 84, 0, false);
        canvas_set_font(canvas, FontSecondary);
        ui_kit_center_text(canvas, 51, "Start a recording", NULL);
        return;
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

/* Visual mapping only: historical tool IDs and the navigation table are left
 * untouched. New pictograms all belong to the same 10x10 family. */
static UiKitIcon labmate_menu_icon_for_tool(uint8_t tool) {
    switch(tool) {
    case LabMateToolGpio:
    case LabMateToolButton:
        return UiKitIconGpio;
    case LabMateToolFrequency:
    case LabMateToolPulse:
        return UiKitIconFreq;
    case LabMateToolGenerator:
        return UiKitIconPwm;
    case LabMateToolUart:
        return UiKitIconUart;
    case LabMateToolI2c:
        return UiKitIconI2c;
    case LabMateToolScope:
        return UiKitIconScope;
    case LabMateToolDoctor:
    case LabMateToolAlerts:
    case LabMateToolOneWire:
        return UiKitIconDoctor;
    case LabMateToolCounter:
    case LabMateToolDashboard:
    case LabMateToolAbout:
        return UiKitIconDash;
    case LabMateToolLogger:
    case LabMateToolHistory:
    case LabMateToolProfiles:
    default:
        return UiKitIconRec;
    }
}

static UiKitIcon labmate_menu_icon_for_group(uint8_t group) {
    switch(group) {
    case LabMateGroupMeasure:
        return UiKitIconCategoryMeasure;
    case LabMateGroupOutput:
        return UiKitIconCategoryOutput;
    case LabMateGroupRecords:
        return UiKitIconCategoryRecords;
    case LabMateGroupComm:
        return UiKitIconCategoryComm;
    case LabMateGroupInfo:
    default:
        return UiKitIconSettings;
    }
}

static const char* labmate_group_name(uint8_t group) {
    static const char* const names[LabMateGroupCount] = {
        "Measure", "Output", "Records", "Comm", "Settings"};
    return group < LabMateGroupCount ? names[group] : "Measure";
}

/* The inherited tool routes are unchanged; only their display text differs. */
static const char* labmate_tool_name(uint8_t tool) {
    switch(tool) {
    case LabMateToolGpio: return "GPIO monitor";
    case LabMateToolFrequency: return "Frequency meter";
    case LabMateToolPulse: return "Pulse analyzer";
    case LabMateToolCounter: return "Event counter";
    case LabMateToolButton: return "Button analyzer";
    case LabMateToolScope: return "Logic scope";
    case LabMateToolDoctor: return "Signal doctor";
    case LabMateToolGenerator: return "PWM studio";
    case LabMateToolAlerts: return "Threshold alerts";
    case LabMateToolLogger: return "Data logger";
    case LabMateToolHistory: return "Log history";
    case LabMateToolProfiles: return "Profiles";
    case LabMateToolDashboard: return "Dashboard";
    case LabMateToolUart: return "UART terminal";
    case LabMateToolI2c: return "I2C explorer";
    case LabMateToolOneWire: return "1-Wire temp";
    case LabMateToolAbout: return "About";
    default: return "Tool";
    }
}

static const char* labmate_tool_short_name(uint8_t tool) {
    switch(tool) {
    case LabMateToolFrequency: return "Frequency";
    case LabMateToolButton: return "Button";
    case LabMateToolAlerts: return "Alerts";
    case LabMateToolDoctor: return "Doctor";
    case LabMateToolI2c: return "I2C";
    case LabMateToolUart: return "UART";
    default: return labmate_tool_name(tool);
    }
}

void draw_menu(Canvas* canvas, LabMateApp* app) {
    const uint8_t count = app->menu_in_group ? labmate_nav_group_size(app->menu_group) :
                                                (uint8_t)LabMateGroupCount;
    const uint8_t selected = app->selected < count ? app->selected : 0U;
    canvas_set_color(canvas, ColorBlack);

    if(!app->menu_in_group) {
        /* Native small-font title/version, frameless icons, two focus lines. */
        ui_kit_brand(canvas);
        ui_kit_carousel_card(canvas, 11, 18, 18, 18, false);
        ui_kit_carousel_card(canvas, 48, 10, 32, 27, true);
        ui_kit_carousel_card(canvas, 99, 18, 18, 18, false);
        const uint8_t prev = (uint8_t)((selected + count - 1U) % count);
        const uint8_t next = (uint8_t)((selected + 1U) % count);
        if(app->ui_carousel_motion && app->ui_frame < UI_KIT_TWEEN_FRAMES) {
            const uint8_t from = app->ui_from;
            const bool forward = app->ui_direction > 0;
            const uint8_t frame = app->ui_frame;
            const uint8_t size_in = (uint8_t)ui_kit_lerp(
                12, 24, frame, UI_KIT_TWEEN_FRAMES);
            const uint8_t size_out = (uint8_t)ui_kit_lerp(
                24, 12, frame, UI_KIT_TWEEN_FRAMES);
            int16_t x_in = ui_kit_lerp(
                forward ? 102 : 14, 52,
                frame, UI_KIT_TWEEN_FRAMES);
            int16_t x_out = ui_kit_lerp(
                52, forward ? 14 : 102,
                frame, UI_KIT_TWEEN_FRAMES);
            const int16_t y_in = ui_kit_lerp(
                21, 10, frame, UI_KIT_TWEEN_FRAMES);
            const int16_t y_out = ui_kit_lerp(
                10, 21, frame, UI_KIT_TWEEN_FRAMES);
            if(frame == UI_KIT_TWEEN_FRAMES - 1U) {
                x_in += forward ? -1 : 1;
                x_out += forward ? 1 : -1;
            }
            const bool from_center = size_out >= 18U && x_out >= 48 && x_out <= 58;
            const bool to_center = size_in >= 18U && x_in >= 48 && x_in <= 58;
            ui_kit_icon(canvas, labmate_menu_icon_for_group(from), x_out, y_out,
                        size_out, !from_center, false, 0U);
            ui_kit_icon(canvas, labmate_menu_icon_for_group(selected), x_in, y_in,
                        size_in, !to_center, false, app->ui_pulse_phase);
        } else {
            ui_kit_icon(canvas, labmate_menu_icon_for_group(prev), 14, 21, 12, true, false, 0U);
            ui_kit_icon(
                canvas, labmate_menu_icon_for_group(selected),
                52, 10, 24,
                false, false, app->ui_pulse_phase);
            ui_kit_icon(canvas, labmate_menu_icon_for_group(next), 102, 21, 12, true, false, 0U);
        }
        canvas_set_font(canvas, FontPrimary);
        ui_kit_center_text(canvas, 46, labmate_group_name(selected), NULL);
        char detail[24];
        const uint8_t items = labmate_nav_group_size(selected);
        if(selected == LabMateGroupInfo)
            (void)snprintf(detail, sizeof(detail), "Language and motion");
        else
            (void)snprintf(detail, sizeof(detail), "%u %s", (unsigned)items,
                           items == 1U ? "tool" : "tools");
        canvas_set_font(canvas, FontSecondary);
        ui_kit_center_text(canvas, 55, detail, NULL);
        ui_kit_page_dots(canvas, selected, count);
        return;
    }

    /* Settings-style list: three complete entries and a readable fourth
     * text hint. No scrollbar or permanent top/bottom bars. */
    ui_kit_back_title(canvas, labmate_group_name(app->menu_group), NULL, NULL);
    const uint8_t first = labmate_nav_first_visible(selected, count, 3U);
    const uint8_t target_y = (uint8_t)(12U + (selected-first)*UI_KIT_LIST_ROW_H);
    uint8_t pill_y = target_y;
    if(app->ui_list_motion && app->ui_frame < UI_KIT_TWEEN_FRAMES) {
        const uint8_t old_first = labmate_nav_first_visible(app->ui_list_previous, count, 3U);
        const uint8_t old_y = (uint8_t)(12U + (app->ui_list_previous-old_first)*UI_KIT_LIST_ROW_H);
        pill_y = (uint8_t)ui_kit_lerp(old_y, target_y, app->ui_frame, UI_KIT_TWEEN_FRAMES);
        if(app->ui_frame == UI_KIT_TWEEN_FRAMES-1U && old_y != target_y)
            pill_y = (uint8_t)(target_y + (old_y < target_y ? 1 : -1));
    }
    ui_kit_pill(canvas, 2, pill_y, 124, 14);
    for(uint8_t row = 0; row < 3U && first+row < count; ++row) {
        const uint8_t index = first + row;
        const uint8_t tool = labmate_nav_tool_at(app->menu_group, index);
        /* During motion, invert the row nearest the moving highlight. */
        const int16_t separation = (int16_t)pill_y - (12 + row*UI_KIT_LIST_ROW_H);
        const bool inverse = separation > -7 && separation < 7;
        ui_kit_list_row(canvas, (uint8_t)(12U + row*UI_KIT_LIST_ROW_H),
                        labmate_menu_icon_for_tool(tool), labmate_tool_name(tool),
                        labmate_tool_short_name(tool), inverse);
    }
    if(first+3U < count) {
        /* Full glyph baseline at 62 prevents a half-cut fourth caption. */
        const uint8_t tool = labmate_nav_tool_at(app->menu_group, first+3U);
        canvas_set_font(canvas, FontSecondary);
        (void)ui_kit_text(canvas, 22, 62, 91, labmate_tool_name(tool),
                          labmate_tool_short_name(tool));
    }
}

/* GPIO pixel target, Step 2: display-only, never reads a pin or changes the
 * GPIO sampling, counter, IRQ, key routing, logging or lease policies.
 * 104 display samples occupy exactly 13 static bytes (not 104 bytes).
 * This cache is protected by the existing viewport/app mutex. */
#define LABMATE_GPIO_TRACE_BITS 104U
#define LABMATE_GPIO_TRACE_BYTES 13U
#define LABMATE_GPIO_TRACE_INTERVAL_MS 40U

typedef struct {
    uint8_t bits[LABMATE_GPIO_TRACE_BYTES];
    const LabMateApp* owner;
    uint32_t last_tick;
    uint8_t pin;
    bool initialized;
} LabMateGpioUiTrace;

static LabMateGpioUiTrace labmate_gpio_trace;

/* Called only by the viewport when GPIO is no longer displayed. A subsequent
 * visit starts with a full window of the selected pin's current level. */
void labmate_gpio_trace_reset_ui(void) {
    labmate_gpio_trace.initialized=false;
    labmate_gpio_trace.owner=NULL;
}

static void labmate_gpio_trace_fill(LabMateGpioUiTrace* trace, bool level) {
    memset(trace->bits,level ? 0xff : 0x00,sizeof(trace->bits));
}

static bool labmate_gpio_trace_bit(const LabMateGpioUiTrace* trace, uint8_t i) {
    return ((trace->bits[i/8U] >> (i%8U)) & 1U) != 0U;
}

static void labmate_gpio_trace_push(LabMateGpioUiTrace* trace, bool level) {
    /* Bit zero is oldest; shift exactly 104 bits toward the left of the
     * displayed wave, and append the newest reading at bit 103. */
    for(uint8_t i=0U;i<LABMATE_GPIO_TRACE_BYTES;++i) {
        const uint8_t carry=(i+1U<LABMATE_GPIO_TRACE_BYTES) ?
                            (uint8_t)((trace->bits[i+1U]&1U)<<7U) : 0U;
        trace->bits[i]=(uint8_t)((trace->bits[i]>>1U)|carry);
    }
    if(level) trace->bits[12U] |= 0x80U;
    else trace->bits[12U] &= (uint8_t)~0x80U;
}

static void labmate_gpio_trace_update(
    LabMateGpioUiTrace* trace, const LabMateApp* app, uint32_t tick, bool valid) {
    if(!valid) {
        trace->initialized=false; /* No fabricated measurement while unowned. */
        return;
    }
    if(!trace->initialized || trace->owner!=app || trace->pin!=app->gpio_index) {
        labmate_gpio_trace_fill(trace,app->gpio_state);
        trace->owner=app;
        trace->pin=app->gpio_index;
        trace->last_tick=tick;
        trace->initialized=true;
    } else if(!app->hold) {
        /* A late frame contributes only one OBSERVED level. Never backfill
         * missed periods with invented observations. */
        const uint32_t interval_ticks=(furi_kernel_get_tick_frequency()*
            LABMATE_GPIO_TRACE_INTERVAL_MS+999U)/1000U;
        const uint32_t interval=interval_ticks ? interval_ticks : 1U;
        if((uint32_t)(tick-trace->last_tick)>=interval) {
            labmate_gpio_trace_push(trace,app->gpio_state);
            trace->last_tick=tick;
        }
    }
}

static void labmate_gpio_pin_strip(Canvas* c, uint8_t selected) {
    /* Original eight labels and their order are consumed directly. */
    if(selected>=GPIO_COUNT || GPIO_COUNT<5U) return;
    uint8_t first=selected>2U ? (uint8_t)(selected-2U) : 0U;
    if(first>GPIO_COUNT-5U) first=GPIO_COUNT-5U;
    canvas_set_font(c,FontSecondary);
    canvas_set_color(c,ColorBlack);
    for(uint8_t i=0U;i<5U;++i) {
        const uint8_t pin=(uint8_t)(first+i);
        const uint8_t x=(uint8_t)(4U+i*24U);
        const uint16_t w=canvas_string_width(c,labmate_gpio_names[pin]);
        if(w>22U) continue; /* Never draw a clipped label. */
        if(pin==selected) {
            canvas_draw_rbox(c,x,12,23,11,3);
            canvas_set_color(c,ColorWhite);
        }
        canvas_draw_str(c,x+(23U-w)/2U,20,labmate_gpio_names[pin]);
        canvas_set_color(c,ColorBlack);
    }
    if(first>0U) {
        canvas_draw_line(c,3,15,0,17);
        canvas_draw_line(c,0,17,3,19);
    }
    if(first+5U<GPIO_COUNT) {
        canvas_draw_line(c,125,15,127,17);
        canvas_draw_line(c,127,17,125,19);
    }
}

static void labmate_gpio_endpoint_disc(Canvas* c,uint8_t x,uint8_t y,uint8_t r) {
    static const uint8_t half3[]={1U,2U,3U,3U,3U,2U,1U};
    static const uint8_t half4[]={1U,2U,3U,4U,4U,4U,3U,2U,1U};
    const uint8_t* half=(r==4U)?half4:half3;
    for(uint8_t i=0U;i<(uint8_t)(2U*r+1U);++i)
        canvas_draw_line(c,x-half[i],(int32_t)y-r+i,x+half[i],(int32_t)y-r+i);
}

static void labmate_gpio_endpoint_hollow(Canvas* c,uint8_t x,uint8_t y) {
    /* Erase wave/rail beneath the hollow endpoint, then draw a circular ring. */
    canvas_set_color(c,ColorWhite);
    labmate_gpio_endpoint_disc(c,x,y,3U);
    canvas_set_color(c,ColorBlack);
    canvas_draw_line(c,x-1U,y-3U,x+1U,y-3U);
    canvas_draw_dot(c,x-2U,y-2U);canvas_draw_dot(c,x+2U,y-2U);
    canvas_draw_dot(c,x-3U,y-1U);canvas_draw_dot(c,x+3U,y-1U);
    canvas_draw_dot(c,x-3U,y);canvas_draw_dot(c,x+3U,y);
    canvas_draw_dot(c,x-3U,y+1U);canvas_draw_dot(c,x+3U,y+1U);
    canvas_draw_dot(c,x-2U,y+2U);canvas_draw_dot(c,x+2U,y+2U);
    canvas_draw_line(c,x-1U,y+3U,x+1U,y+3U);
}

static void labmate_gpio_signal_panel(
    Canvas* c,const LabMateGpioUiTrace* trace,bool valid,bool held,bool pulse) {
    canvas_set_color(c,ColorBlack);
    canvas_draw_rframe(c,4,25,120,19,3);
    for(uint8_t x=8U;x<=117U;x+=3U) {
        canvas_draw_dot(c,x,29);
        canvas_draw_dot(c,x,40);
    }
    if(!valid || !trace->initialized) return;
    bool prior=labmate_gpio_trace_bit(trace,0U);
    for(uint8_t i=0U;i<LABMATE_GPIO_TRACE_BITS;++i) {
        const bool value=labmate_gpio_trace_bit(trace,i);
        const uint8_t x=(uint8_t)(9U+i);
        const uint8_t y=value ? 29U : 40U;
        if(i>0U && value!=prior) canvas_draw_line(c,x,29,x,40);
        canvas_draw_dot(c,x,y);
        prior=value;
    }
    /* Pulse r=4 at low y=40 would cross the panel bottom by 1px.
     * Move only this marker UP 1px, within the approved 2px tolerance. */
    const uint8_t endpoint_y=prior ? 29U : ((pulse && !held) ? 39U : 40U);
    if(held) labmate_gpio_endpoint_hollow(c,113,endpoint_y);
    else labmate_gpio_endpoint_disc(c,113,endpoint_y,pulse ? 4U : 3U);
}

static void labmate_gpio_level_marker(Canvas* c,bool high) {
    canvas_set_color(c,ColorBlack);
    if(high) {
        canvas_draw_dot(c,7,46);canvas_draw_line(c,6,47,8,47);
        canvas_draw_line(c,5,48,9,48);canvas_draw_line(c,6,49,8,49);
        canvas_draw_dot(c,7,50);
    } else {
        canvas_draw_line(c,6,46,8,46);
        canvas_draw_dot(c,5,47);canvas_draw_dot(c,9,47);
        canvas_draw_dot(c,5,48);canvas_draw_dot(c,9,48);
        canvas_draw_dot(c,5,49);canvas_draw_dot(c,9,49);
        canvas_draw_line(c,6,50,8,50);
    }
}

void draw_gpio(Canvas* canvas, LabMateApp* app) {
    if(!canvas || !app || app->gpio_index>=GPIO_COUNT) return;
    const UiKitInstrumentState state=app->monitor_release_fault ?
        UiKitInstrumentError : app->monitor_blocked ? UiKitInstrumentBusy :
        !app->monitor_active ? UiKitInstrumentReady :
        app->hold ? UiKitInstrumentHeld : UiKitInstrumentLive;
    const bool valid=app->monitor_active && !app->monitor_blocked &&
                     !app->monitor_release_fault;
    const uint32_t now=furi_get_tick();
    const bool pulse=((now/500U)&1U)!=0U;
    labmate_gpio_trace_update(&labmate_gpio_trace,app,now,valid);
    canvas_set_color(canvas,ColorBlack);
    canvas_draw_line(canvas,5,2,2,5);
    canvas_draw_line(canvas,2,5,5,8);
    canvas_set_font(canvas,FontPrimary);
    const char* title="GPIO monitor";
    uint16_t title_width=canvas_string_width(canvas,title);
    canvas_set_font(canvas,FontSecondary);
    const uint8_t chip_width=ui_kit_state_chip_width(canvas,state);
    if(chip_width>0U) {
        const uint8_t chip_x=(uint8_t)(127U-chip_width);
        uint8_t title_x=9U;
        if(title_x+title_width+2U>chip_x) title_x=7U; /* <=2 px */
        if(title_x+title_width+1U>chip_x) {
            /* Never silently omit the title or let it collide. If a future
             * E11 primary font is unexpectedly wide, show a complete short
             * title in the approved FontPrimary, not clipped characters. */
            title="GPIO";
            title_x=9U;
            canvas_set_font(canvas,FontPrimary);
            title_width=canvas_string_width(canvas,title);
            canvas_set_font(canvas,FontSecondary);
        }
        if(title_x+title_width+1U<=chip_x) {
            canvas_set_font(canvas,FontPrimary);
            canvas_draw_str(canvas,title_x,9,title);
        }
        (void)ui_kit_state_chip(canvas,state,pulse);
    }
    labmate_gpio_pin_strip(canvas,app->gpio_index);
    labmate_gpio_signal_panel(canvas,&labmate_gpio_trace,valid,app->hold,pulse);
    if(valid) labmate_gpio_level_marker(canvas,app->gpio_state);
    canvas_set_font(canvas,FontPrimary);
    if(valid) canvas_draw_str(canvas,13,52,app->gpio_state ? "High" : "Low");
    else canvas_draw_str(canvas,13,52,"-");

    /* Keep the complete integer and pluralization where they fit; extremely
     * large counts omit the label rather than crop or overlap the level. */
    char count[16];
    snprintf(count,sizeof(count),"%lu",(unsigned long)app->edges);
    const char* suffix=app->edges==1U ? " change" : " changes";
    canvas_set_font(canvas,FontPrimary);
    const uint16_t level_end=(uint16_t)(13U+canvas_string_width(canvas,
                                valid ? (app->gpio_state ? "High" : "Low") : "-"));
    const uint16_t number_width=canvas_string_width(canvas,valid?count:"-");
    canvas_set_font(canvas,FontSecondary);
    const uint16_t suffix_width=canvas_string_width(canvas,suffix);
    const bool show_suffix=valid && (number_width+suffix_width+4U+level_end<=123U);
    const uint16_t group_width=number_width+(show_suffix ? suffix_width : 0U);
    const int16_t start=123-(int16_t)group_width;
    if(start>=0 && start>=(int16_t)(level_end+3U)) {
        canvas_set_font(canvas,FontPrimary);
        canvas_draw_str(canvas,start,52,valid?count:"-");
        if(show_suffix) {
            canvas_set_font(canvas,FontSecondary);
            canvas_draw_str(canvas,start+number_width,52,suffix);
        }
    }
    (void)ui_kit_key_hint(canvas,4U,UiKitKeyLeftRight,"Pin");
    (void)ui_kit_key_hint(canvas,70U,UiKitKeyOk,app->hold ? "Resume" : "Hold");
    canvas_set_color(canvas,ColorBlack);
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

static void frequency_format_tiny(char* text, size_t size, uint32_t mhz, bool valid) {
    if(!valid) (void)snprintf(text, size, "--");
    else if(mhz >= 1000000000U)
        (void)snprintf(text, size, "%luM", (unsigned long)(mhz / 1000000000U));
    else if(mhz >= 1000000U)
        (void)snprintf(text, size, "%luk", (unsigned long)(mhz / 1000000U));
    else (void)snprintf(text, size, "%luHz", (unsigned long)(mhz / 1000U));
}

/* Presentation-only frequency conversion. The measured millihertz, capture
 * policy, stored extrema and CSV output remain completely untouched. */
static void frequency_hero_text(
    char* value, size_t size, const char** unit, uint32_t millihz) {
    if(millihz >= 1000000000U) {
        const uint32_t hundredths = millihz / 10000000U;
        snprintf(value, size, "%lu.%02lu", (unsigned long)(hundredths / 100U),
                 (unsigned long)(hundredths % 100U));
        *unit = "MHz";
    } else if(millihz >= 1000000U) {
        const uint32_t hundredths = millihz / 10000U;
        snprintf(value, size, "%lu.%02lu", (unsigned long)(hundredths / 100U),
                 (unsigned long)(hundredths % 100U));
        *unit = "kHz";
    } else {
        const uint32_t hz = millihz / 1000U;
        const uint32_t hundredths = (millihz % 1000U) / 10U;
        snprintf(value, size, "%lu.%02lu", (unsigned long)hz,
                 (unsigned long)hundredths);
        *unit = "Hz";
    }
}

void draw_frequency(Canvas* canvas, LabMateApp* app) {
    const bool high_mode = app->gpio_index == 4U;
    char value[20];
    char min_value[20];
    char max_value[20];
    char max_tiny[20];
    ui_kit_back_title(canvas, "Frequency", NULL, high_mode ? "PB3" : "PC1");

    if(app->frequency_valid) {
        const char* unit = "Hz";
        frequency_hero_text(value, sizeof(value), &unit, app->frequency_millihz);
        canvas_set_color(canvas, ColorBlack);
        canvas_set_font(canvas, FontBigNumbers);
        if(canvas_current_font_height(canvas) > 22U ||
           canvas_string_width(canvas, value) > 86U) {
            canvas_set_font(canvas, FontPrimary);
        }
        /* Fixed number endpoint and unit origin: no sideways jumping. */
        canvas_draw_str_aligned(canvas, 94, 32, AlignRight, AlignBottom, value);
        canvas_set_font(canvas, FontSecondary);
        (void)ui_kit_text(canvas, 100, 30, 26, unit, NULL);
    } else {
        canvas_set_font(canvas, FontPrimary);
        ui_kit_center_text(canvas, 31, "No signal", NULL);
    }

    const bool alert = app->threshold.armed && app->threshold.latched &&
                       app->threshold.source == LabMateAlertFrequency;
    const bool drifting = app->frequency_stats_valid &&
                          app->frequency_min_millihz > 0U &&
                          app->frequency_max_millihz - app->frequency_min_millihz >
                              app->frequency_min_millihz / 20U;
    const char* status = alert ? "Alert" : app->capture_blocked ? "Busy" :
                         app->hold ? "Held" : !app->frequency_valid ? "No signal" :
                         drifting ? "Drifting" : "Stable";
    canvas_set_font(canvas, FontSecondary);
    (void)ui_kit_text(canvas, 4, 41, 74, status, NULL);
    ui_kit_pulse_line(canvas, 87, 39, 36, app->ui_pulse_phase, app->frequency_valid && !app->hold);

    frequency_format_compact(
        min_value, sizeof(min_value), app->frequency_min_millihz, app->frequency_stats_valid);
    frequency_format_compact(
        max_value, sizeof(max_value), app->frequency_max_millihz, app->frequency_stats_valid);
    canvas_set_font(canvas, FontSecondary);
    (void)ui_kit_text(canvas, 4, 49, 17, "Min", NULL);
    (void)ui_kit_text(canvas, 25, 49, 42, min_value, "--");
    (void)ui_kit_text(canvas, 73, 49, 20, "Max", NULL);
    const char* max_label = max_value;
    if(canvas_string_width(canvas, max_label) > 35U) {
        frequency_format_tiny(
            max_tiny, sizeof(max_tiny), app->frequency_max_millihz,
            app->frequency_stats_valid);
        max_label = max_tiny;
    }
    if(canvas_string_width(canvas, max_label) <= 35U)
        canvas_draw_str_aligned(canvas, 125, 49, AlignRight, AlignBottom, max_label);

    /* A real sample-history trace of normalized measured frequency values.
     * The display makes no claim to show an oscilloscope edge waveform. */
    if(app->frequency_valid && app->ui_frequency_trace_count) {
        uint8_t history[100];
        const uint8_t n = app->ui_frequency_trace_count;
        const uint8_t first = (app->ui_frequency_trace_head + 100U - n) % 100U;
        for(uint8_t i = 0; i < n; ++i)
            history[i] = app->ui_frequency_trace[(first + i) % 100U];
        ui_kit_sparkline(canvas, history, n, 3, 53, 122, 10);
    } else {
        ui_kit_pulse_line(canvas, 17, 57, 94, 0, false);
    }
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

/* Event Counter pixel target, Step 3: PASSIVE PB3/TIM2 rising-edge
 * presentation only. The existing capture, STOP/RESUME, reset, timer,
 * threshold, GPIO and storage paths remain completely unchanged. */
static void labmate_counter_ui_count(char* out, size_t size, uint64_t count) {
    if(count < 1000000ULL) {
        if(!labmate_counter_format(count,out,size)) snprintf(out,size,"-");
        return;
    }
    const bool billions = count >= 1000000000ULL;
    const uint64_t divisor = billions ? 1000000000ULL : 1000000ULL;
    const uint64_t integer = count/divisor;
    const uint8_t decimal = (uint8_t)((count%divisor)/
                                      (billions ? 100000000ULL : 10000ULL));
    char whole[24];
    if(!labmate_counter_format(integer,whole,sizeof(whole))) {
        snprintf(out,size,"-");
        return;
    }
    const size_t digits = strlen(whole);
    const size_t suffix = billions ? 3U : 4U;
    if(digits + suffix >= size) { snprintf(out,size,"-"); return; }
    memcpy(out,whole,digits);
    out[digits] = '.';
    if(billions) {
        out[digits+1U] = (char)('0' + decimal);
        out[digits+2U] = 'G';
        out[digits+3U] = '\0';
    } else {
        out[digits+1U] = (char)('0' + decimal/10U);
        out[digits+2U] = (char)('0' + decimal%10U);
        out[digits+3U] = 'M';
        out[digits+4U] = '\0';
    }
}

static void labmate_counter_ui_time(char* out, size_t size, uint32_t seconds) {
    if(seconds < 60U)
        snprintf(out,size,"%lu s",(unsigned long)seconds);
    else if(seconds < 3600U)
        snprintf(out,size,"%lu:%02lu",(unsigned long)(seconds/60U),
                 (unsigned long)(seconds%60U));
    else
        snprintf(out,size,"%lu:%02lu:%02lu",(unsigned long)(seconds/3600U),
                 (unsigned long)((seconds/60U)%60U),
                 (unsigned long)(seconds%60U));
}

void draw_counter(Canvas* canvas, LabMateApp* app) {
    char count[24];
    char time_text[24];
    /* RESET/entry clears these markers; STOP retains them even if no
     * edges arrived. An extremely early zero-tick START/STOP can be
     * ambiguous without changing app state (out of this UI-only scope). */
    const bool started_this_visit = app->counter_start_tick != 0U ||
        app->counter_elapsed_ticks != 0U || app->counter_total != 0U;
    const UiKitInstrumentState state = app->capture_release_fault ?
        UiKitInstrumentError : app->capture_blocked ? UiKitInstrumentBusy :
        app->counter_active ? UiKitInstrumentLive :
        started_this_visit ? UiKitInstrumentStopped : UiKitInstrumentReady;
    const bool valid = state != UiKitInstrumentBusy && state != UiKitInstrumentError;
    const bool alert = app->threshold.armed && app->threshold.latched &&
                       app->threshold.source == LabMateAlertCounter;
    const bool pulse = (furi_get_tick()/500U % 2U) != 0U;
    canvas_set_color(canvas,ColorBlack);
    /* Exact header: back chevron, x=9 Primary title, right-anchored chip. */
    canvas_draw_line(canvas,5,2,2,5);
    canvas_draw_line(canvas,2,5,5,8);
    canvas_set_font(canvas,FontPrimary);
    canvas_draw_str(canvas,9,9,"Counter");
    (void)ui_kit_state_chip(canvas,state,pulse);

    canvas_set_font(canvas,FontSecondary);
    /* Active threshold remains visible, without displaying TIM2/RISE. */
    const char* context = alert ? "Rising edges on PB3 !" : "Rising edges on PB3";
    if(canvas_string_width(canvas,context)<=120U)
        canvas_draw_str(canvas,4,20,context);
    canvas_draw_str(canvas,5,32,"Count");
    canvas_draw_str(canvas,84,32,"Time");

    if(valid) {
        labmate_counter_ui_count(count,sizeof(count),app->counter_total);
        labmate_counter_ui_time(time_text,sizeof(time_text),app->counter_elapsed_seconds);
    } else {
        snprintf(count,sizeof(count),"-");
        snprintf(time_text,sizeof(time_text),"-");
    }
    canvas_set_font(canvas,FontBigNumbers);
    if(canvas_string_width(canvas,count)>78U) {
        /* Extreme 64-bit totals cannot fit on a 78px BigNumbers display.
         * Preserve exact application counter, show an explicit lower bound. */
        snprintf(count,sizeof(count),">9999G");
    }
    if(canvas_string_width(canvas,count)<=78U)
        canvas_draw_str(canvas,4,50,count);

    canvas_set_font(canvas,FontPrimary);
    /* Real FontPrimary glyph widths vary by firmware. At most a 2px left
     * shift is allowed; when still too wide, keep the hours/minutes and
     * mark their resolution explicitly rather than overlap Count/Time. */
    int16_t time_x=84;
    const uint16_t tw=canvas_string_width(canvas,time_text);
    if(tw>44U && tw<=46U) time_x=82;
    else if(tw>46U && app->counter_elapsed_seconds>=3600U && valid) {
        const uint32_t hours=app->counter_elapsed_seconds/3600U;
        if(hours<=99U)
            snprintf(time_text,sizeof(time_text),"%luh%02lum",
                     (unsigned long)hours,
                     (unsigned long)((app->counter_elapsed_seconds/60U)%60U));
        else snprintf(time_text,sizeof(time_text),">99h");
    }
    if(canvas_string_width(canvas,time_text)<=128U-(uint16_t)time_x)
        canvas_draw_str(canvas,time_x,50,time_text);

    if(state==UiKitInstrumentLive) {
        (void)ui_kit_key_hint(canvas,4U,UiKitKeyOk,"Stop");
    } else if(state==UiKitInstrumentStopped) {
        (void)ui_kit_key_hint(canvas,4U,UiKitKeyOk,"Resume");
        (void)ui_kit_key_hint(canvas,72U,UiKitKeyUp,"Reset");
    } else if(state==UiKitInstrumentReady) {
        (void)ui_kit_key_hint(canvas,4U,UiKitKeyOk,"Start");
    }
    canvas_set_color(canvas,ColorBlack);
}

/* Display-only PWM Studio renderer. No TIM1 / GPIO writes here. */
void draw_generator(Canvas* canvas, LabMateApp* app) {
    char value[24];
    char duty[12];
    const uint32_t freq = labmate_generator_frequency(app);
    const char* unit = freq >= 1000U ? "kHz" : "Hz";
    ui_kit_back_title(canvas, "PWM studio", "PWM", "PA7");
    if(freq >= 1000U) {
        snprintf(value, sizeof(value), "%lu.%03lu", (unsigned long)(freq/1000U),
                 (unsigned long)(freq%1000U));
    } else snprintf(value, sizeof(value), "%lu", (unsigned long)freq);
    snprintf(duty, sizeof(duty), "%u%%", (unsigned)app->generator_duty_percent);
    canvas_set_font(canvas, FontBigNumbers);
    if(canvas_current_font_height(canvas) > 22U ||
       canvas_string_width(canvas, value) > 86U) canvas_set_font(canvas, FontPrimary);
    canvas_draw_str_aligned(canvas, 94, 32, AlignRight, AlignBottom, value);
    canvas_set_font(canvas, FontSecondary);
    (void)ui_kit_text(canvas, 100, 30, 26, unit, NULL);
    const char* state = app->generator_release_fault ? "Error" :
                        app->generator_blocked ? "Busy" :
                        app->generator_editing ? "Editing" :
                        app->generator_running ? "Running" : "Stopped";
    (void)ui_kit_text(canvas, 4, 41, 73, state, NULL);
    ui_kit_pulse_line(canvas, 87, 39, 36, app->ui_pulse_phase, app->generator_running);
    (void)ui_kit_text(canvas, 4, 49, 30, "Duty", NULL);
    (void)ui_kit_text(canvas, 39, 49, 35, duty, NULL);
    if(app->generator_editing) {
        char step[24];
        snprintf(step, sizeof(step), "Step %lu Hz",
                 (unsigned long)labmate_generator_custom_step_hz(app));
        (void)ui_kit_text(canvas, 76, 49, 50, step, "Edit");
    } else {
        (void)ui_kit_text(canvas, 80, 49, 47, "Up/down", "Adjust");
    }

    /* This is a diagram of the configured duty cycle, not an acquired trace. */
    canvas_draw_line(canvas, 4, 61, 10, 61);
    canvas_draw_line(canvas, 10, 61, 10, 55);
    const uint8_t end = (uint8_t)(10U + (uint16_t)app->generator_duty_percent*108U/100U);
    canvas_draw_line(canvas, 10, 55, end, 55);
    canvas_draw_line(canvas, end, 55, end, 61);
    canvas_draw_line(canvas, end, 61, 124, 61);
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
    char duty[24] = "--";
    ui_kit_back_title(canvas, "Pulse", NULL, labmate_gpio_names[app->gpio_index]);

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
        snprintf(duty, sizeof(duty), "%lu.%lu%%",
                 (unsigned long)(app->pulse_duty_permille / 10U),
                 (unsigned long)(app->pulse_duty_permille % 10U));
    }
    if(app->pulse_period_valid) {
        canvas_set_font(canvas, FontBigNumbers);
        if(canvas_current_font_height(canvas) > 22U ||
           canvas_string_width(canvas, duty) > 102U) canvas_set_font(canvas, FontPrimary);
        ui_kit_center_text(canvas, 32, duty, NULL);
    } else {
        canvas_set_font(canvas, FontPrimary);
        ui_kit_center_text(canvas, 31, "No signal", NULL);
    }
    const char* state = app->capture_blocked ? "Busy" : app->hold ? "Held" :
                        app->pulse_period_valid ? "Live" : "No signal";
    canvas_set_font(canvas, FontSecondary);
    (void)ui_kit_text(canvas, 4, 41, 72, state, NULL);
    ui_kit_pulse_line(canvas, 87, 39, 36, app->ui_pulse_phase,
                      app->pulse_period_valid && !app->hold);
    (void)ui_kit_text(canvas, 4, 49, 21, "High", NULL);
    (void)ui_kit_text(canvas, 29, 49, 36, high, "--");
    (void)ui_kit_text(canvas, 73, 49, 19, "Low", NULL);
    (void)ui_kit_text(canvas, 95, 49, 31, low, "--");
    if(app->pulse_period_valid) {
        const uint8_t end = (uint8_t)(10U + (uint32_t)app->pulse_duty_permille*108U/1000U);
        canvas_draw_line(canvas, 4, 61, 10, 61);
        canvas_draw_line(canvas, 10, 61, 10, 55);
        canvas_draw_line(canvas, 10, 55, end, 55);
        canvas_draw_line(canvas, end, 55, end, 61);
        canvas_draw_line(canvas, end, 61, 124, 61);
    } else ui_kit_pulse_line(canvas, 17, 58, 94, 0, false);
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


