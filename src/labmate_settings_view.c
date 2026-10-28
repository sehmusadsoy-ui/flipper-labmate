#include "labmate_settings_view.h"
#include "ui_kit.h"

/* Display-only names: persisted identifiers/record lengths are unchanged. */
static const char* const labels[] = {
    "Language", "Motion", "Startup intro", "Info", "Reset UI",
};

static UiKitSettingsOptionKind option_kind(uint8_t index) {
    if(index == 0U) return UiKitSettingsOptionValue;
    if(index == 1U || index == 2U) return UiKitSettingsOptionToggle;
    if(index == 3U) return UiKitSettingsOptionLink;
    return UiKitSettingsOptionDestructive;
}

static void draw_language(Canvas* c) {
    ui_kit_back_title(c, "Language", NULL, NULL);
    ui_kit_pill(c, 2, 13, 124, 13);
    canvas_set_color(c, ColorWhite);
    canvas_set_font(c, FontSecondary);
    (void)ui_kit_text(c, 6, 22, 100, "English", NULL);
    /* Check mark is procedural: no dependency on a Unicode font glyph. */
    canvas_draw_line(c, 110, 19, 113, 22);
    canvas_draw_line(c, 113, 22, 119, 16);
    canvas_set_color(c, ColorBlack);
    canvas_set_font(c, FontSecondary);
    (void)ui_kit_text(c, 6, 39, 116, "More languages", NULL);
    (void)ui_kit_text(c, 6, 49, 116, "Coming soon", NULL);
}

static void draw_reset_dialog(Canvas* c, bool confirm_selected) {
    canvas_set_font(c, FontSecondary);
    /* Preserve the full meaning at both normal and wide font widths. */
    if(canvas_string_width(c, "Language and settings") <= 108U &&
       canvas_string_width(c, "go back to defaults.") <= 108U) {
        ui_kit_confirmation_details(
            c, confirm_selected,
            "Language and settings", "go back to defaults.", "Your logs stay.");
    } else {
        ui_kit_confirmation_details(
            c, confirm_selected,
            "Settings return to", "their defaults.", "Your logs stay.");
    }
}

void labmate_settings_draw_animated(
    Canvas* c, const LabMateUiPreferences* prefs,
    uint8_t selected, LabMateSettingsPage page, uint8_t notice, bool busy,
    bool reset_confirm_selected, const LabMateSettingsVisual* visual) {
    if(!c || !prefs || selected > 4U) return;
    canvas_set_color(c, ColorBlack);
    if(page == LabMateSettingsLanguage) {
        draw_language(c);
        return;
    }
    ui_kit_back_title(c, "Settings", NULL, NULL);

    const uint8_t previous = visual && visual->selection_motion &&
                                     visual->previous_selected < 5U ?
        visual->previous_selected : selected;
    const uint8_t frame = visual && visual->selection_motion ?
        visual->selection_frame : UI_KIT_TWEEN_FRAMES;
    const int16_t from_scroll = previous > 2U ? (int16_t)(previous - 2U)*13 : 0;
    const int16_t to_scroll = selected > 2U ? (int16_t)(selected - 2U)*13 : 0;
    const int16_t scroll = ui_kit_lerp(from_scroll, to_scroll, frame, UI_KIT_TWEEN_FRAMES);
    const int16_t from_pill = 13 + (int16_t)previous*13 - from_scroll;
    const int16_t to_pill = 13 + (int16_t)selected*13 - to_scroll;
    int16_t pill_y = ui_kit_lerp(from_pill, to_pill, frame, UI_KIT_TWEEN_FRAMES);
    if(visual && visual->selection_motion && frame == UI_KIT_TWEEN_FRAMES - 1U &&
       from_pill != to_pill)
        pill_y = to_pill + (from_pill < to_pill ? 1 : -1);
    if(pill_y >= 13 && pill_y <= 51)
        ui_kit_pill(c, 2, (uint8_t)pill_y, 124, 13);

    for(uint8_t index = 0U; index < 5U; ++index) {
        const int16_t row_y = 13 + (int16_t)index*13 - scroll;
        /* Whole glyphs only. No label is ever clipped by the LCD border. */
        if(row_y < 13 || row_y > 51) continue;
        const bool inverse = pill_y - row_y > -7 && pill_y - row_y < 7;
        const char* value = index == 0U ? "English" : NULL;
        const bool switch_on = index == 1U ? prefs->animations : prefs->startup_animation;
        uint8_t switch_frame = 4U;
        if(visual && visual->toggle_motion && visual->toggle_index == index)
            switch_frame = visual->toggle_frame;
        (void)ui_kit_settings_option_row(
            c, (uint8_t)row_y, labels[index], value, option_kind(index),
            inverse, switch_on, switch_frame);
    }

    /* Partial fourth row is a non-textual cue; letters cannot be cut. */
    const int16_t fourth_y = 13 + 39 - scroll;
    if(fourth_y > 51 && fourth_y < 63) {
        canvas_set_color(c, ColorBlack);
        for(uint8_t x = 6; x < 25; x += 4U)
            canvas_draw_dot(c, x, (uint8_t)(fourth_y + 1U));
    }

    if(page == LabMateSettingsReset) {
        draw_reset_dialog(c, reset_confirm_selected);
        return;
    }
    if(busy) {
        canvas_set_font(c, FontSecondary);
        (void)ui_kit_text(c, 7, 62, 111, "Saving...", NULL);
    } else if(notice == 2U) {
        /* A storage error must never receive a misleading checkmark. */
        ui_kit_panel(c, 27, 48, 74, 15);
        canvas_set_font(c, FontSecondary);
        (void)ui_kit_text(c, 33, 59, 63, "Save failed", NULL);
    } else if(notice == 1U && visual && visual->toast_progress) {
        ui_kit_toast(c, visual->toast_reset ? "Reset" : "Saved", visual->toast_progress);
    }
}

/* Compatibility for existing isolated host tests. Production uses its own
 * visual-only state; no persistent preference field has changed. */
void labmate_settings_draw_content(
    Canvas* c, const LabMateUiPreferences* prefs,
    uint8_t selected, LabMateSettingsPage page, uint8_t notice, bool busy,
    bool reset_confirm_selected) {
    labmate_settings_draw_animated(c, prefs, selected, page, notice, busy,
                                   reset_confirm_selected, NULL);
}

