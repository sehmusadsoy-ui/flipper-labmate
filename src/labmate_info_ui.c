#include "labmate_info_ui.h"
#include "labmate_info_qr_matrix.h"
#include "labmate_info_guides.h"
#include "ui_kit.h"

/* Monochrome presentation only. Font widths must be checked in pixels,
 * never inferred from the number of characters. */

static void guide_dither_fade(Canvas* canvas, uint8_t strength);

static bool info_line_shifted(
    Canvas* canvas, int16_t x, uint8_t y, uint8_t max_width,
    const char* text, int8_t slide_px) {
    x += slide_px;
    if(x < 0 || x > 125) return false;
    uint16_t available = (uint16_t)(126 - x);
    if(available > max_width) available = max_width;
    canvas_set_font(canvas, FontSecondary);
    return ui_kit_text(canvas, x, y, (uint8_t)available, text, NULL);
}

static void info_list_row_shifted(
    Canvas* canvas, uint8_t y, UiKitIcon icon, const char* title,
    const char* short_title, bool selected, int8_t slide_px) {
    if(selected) ui_kit_pill(canvas, 2U, y, 124U, 13U);
    if(slide_px == 0) {
        ui_kit_list_row(canvas, y, icon, title, short_title, selected);
        return;
    }
    const int16_t icon_x = 6 + slide_px;
    const int16_t text_x = 22 + slide_px;
    if(icon_x >= 0 && icon_x <= 118)
        ui_kit_icon(canvas, icon, icon_x, y + 2U, 10U, false, selected, 0U);
    canvas_set_color(canvas, selected ? ColorWhite : ColorBlack);
    if(text_x >= 0 && text_x <= 125) {
        canvas_set_font(canvas, FontSecondary);
        uint16_t width = (uint16_t)(126 - text_x);
        if(width > 91U) width = 91U;
        (void)ui_kit_text(canvas, text_x, y + 10U,
                          (uint8_t)width, title, short_title);
    }
    const int16_t arrow_x = 118 + slide_px;
    if(arrow_x >= 0 && arrow_x <= 122) {
        canvas_draw_line(canvas, arrow_x, y + 5U, arrow_x + 3, y + 7U);
        canvas_draw_line(canvas, arrow_x + 3, y + 7U, arrow_x, y + 9U);
    }
    canvas_set_color(canvas, ColorBlack);
}

static void info_home_item(
    Canvas* canvas, uint8_t y, uint8_t index, bool selected, int8_t slide_px) {
    static const char* const names[LABMATE_INFO_ITEM_COUNT] = {
        "Tool guides", "Project", "Safety",
    };
    static const UiKitIcon icons[LABMATE_INFO_ITEM_COUNT] = {
        UiKitIconInfo, UiKitIconRec, UiKitIconGpio,
    };
    info_list_row_shifted(canvas, y, icons[index], names[index], NULL, selected, slide_px);
}

void labmate_info_draw_home_motion(
    Canvas* canvas, uint8_t selected, uint8_t pulse_phase,
    int8_t slide_px, uint8_t fade_strength) {
    if(!canvas) return;
    if(selected >= LABMATE_INFO_ITEM_COUNT) selected = 0U;
    ui_kit_back_title(canvas, "Info", NULL, NULL);
    if(selected == 0U) {
        /* The identity card travels with the list: when selected moves down,
         * the whole card scrolls above the display and the three rows fit. */
        (void)ui_kit_info_identity_card(
            canvas, 13U, (uint8_t)(pulse_phase > 6U ? 6U : pulse_phase));
        info_home_item(canvas, 43U, 0U, true, slide_px);
        /* Peek of the next row: non-text cue, never a clipped glyph. */
        canvas_draw_line(canvas, 6, 62, 18, 62);
    } else {
        for(uint8_t i = 0U; i < LABMATE_INFO_ITEM_COUNT; ++i) {
            info_home_item(canvas, (uint8_t)(14U + i * 14U),
                           i, i == selected, slide_px);
        }
    }
    guide_dither_fade(canvas, fade_strength);
}

void labmate_info_draw_home(Canvas* canvas, uint8_t selected, uint8_t pulse_phase) {
    labmate_info_draw_home_motion(canvas, selected, pulse_phase, 0, 0U);
}

/* Step 3: three entirely visible 14px list rows at a time. The selected row
 * moves through all 17 IDs without truncating or scrolling half a text line. */
void labmate_info_draw_guide_list_motion(
    Canvas* canvas, uint8_t selected, int8_t slide_px, uint8_t fade_strength) {
    if(!canvas) return;
    if(selected >= LABMATE_INFO_GUIDE_COUNT) selected = 0U;
    ui_kit_back_title(canvas, "Tool guides", NULL, NULL);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str_aligned(canvas, 126, 9, AlignRight, AlignBottom, "17 guides");

    const uint8_t first = selected < 2U ? 0U : (uint8_t)(selected - 2U);
    for(uint8_t row = 0U; row < 3U; ++row) {
        const uint8_t index = (uint8_t)(first + row);
        if(index >= LABMATE_INFO_GUIDE_COUNT) break;
        const LabMateInfoGuide* guide = labmate_info_guide(index);
        if(!guide) continue;
        const uint8_t y = (uint8_t)(15U + row * 14U);
        const bool active = selected == index;
        info_list_row_shifted(canvas, y, guide->icon, guide->title,
                              guide->short_title, active, slide_px);
    }
    guide_dither_fade(canvas, fade_strength);
    /* The scroll thumb is the only vertical orientation aid: 17 entries. */
    ui_kit_guide_scroll_thumb(canvas, 14U, 50U,
                              (uint16_t)(LABMATE_INFO_GUIDE_COUNT * 14U),
                              (uint16_t)(first * 14U));
}

void labmate_info_draw_guide_list(Canvas* canvas, uint8_t selected) {
    labmate_info_draw_guide_list_motion(canvas, selected, 0, 0U);
}

static bool guide_baseline_visible(int16_t baseline) {
    /* Secondary font 8px: keep the entire glyph below the fixed header. */
    return baseline >= 21 && baseline <= 63;
}

static void guide_secondary_line(
    Canvas* canvas, int16_t baseline, const char* str, int8_t slide_px) {
    if(!str || !guide_baseline_visible(baseline)) return;
    const int16_t x = 6 + slide_px;
    if(x < 0 || x > 125) return;
    uint16_t width = (uint16_t)(126 - x);
    if(width > 116U) width = 116U;
    canvas_set_font(canvas, FontSecondary);
    (void)ui_kit_text(canvas, x, baseline, (uint8_t)width, str, NULL);
}

int16_t labmate_info_scroll_pixel(int16_t from, int16_t to, uint8_t frame) {
    if(frame >= UI_KIT_TWEEN_FRAMES) return to;
    /* A single real pixel of overshoot, then settle on the final frame. */
    if(frame == UI_KIT_TWEEN_FRAMES - 1U && from != to)
        return (int16_t)(to + (from < to ? 1 : -1));
    return ui_kit_lerp(from, to, frame, UI_KIT_TWEEN_FRAMES);
}

int8_t labmate_info_slide_pixel(uint8_t frame, int8_t direction) {
    if(frame >= UI_KIT_TWEEN_FRAMES) return 0;
    const int8_t dir = direction < 0 ? -1 : 1;
    if(frame < 3U)
        return (int8_t)(-dir * ui_kit_lerp(0, 8, frame, 3U));
    if(frame == UI_KIT_TWEEN_FRAMES - 1U) return (int8_t)-dir;
    return (int8_t)(dir * ui_kit_lerp(8, 0, frame - 3U, 3U));
}

uint8_t labmate_info_fade_strength(uint8_t frame) {
    static const uint8_t steps[UI_KIT_TWEEN_FRAMES + 1U] = {
        0U, 6U, 13U, 13U, 6U, 1U, 0U,
    };
    return steps[frame > UI_KIT_TWEEN_FRAMES ? UI_KIT_TWEEN_FRAMES : frame];
}

static void guide_dither_fade(Canvas* canvas, uint8_t strength) {
    if(!strength) return;
    if(strength > 16U) strength = 16U;
    static const uint8_t pattern[4][4] = {
        {0U, 8U, 2U, 10U}, {12U, 4U, 14U, 6U},
        {3U, 11U, 1U, 9U}, {15U, 7U, 13U, 5U},
    };
    /* Erase a distributed fraction of monochrome ink with white pixels;
     * never darken the empty paper. Header y0..13 and scroll thumb x127
     * are left untouched so orientation stays stable during motion. */
    canvas_set_color(canvas, ColorWhite);
    for(uint8_t y = 14U; y < 64U; ++y)
        for(uint8_t x = 0U; x < 126U; ++x)
            if(pattern[y & 3U][x & 3U] < strength)
                canvas_draw_dot(canvas, x, y);
    canvas_set_color(canvas, ColorBlack);
}

static void guide_card_title_shifted(
    Canvas* canvas, int16_t y, const LabMateInfoGuide* guide, int8_t slide_px) {
    if(y < 14 || y > 52) return;
    if(slide_px == 0) {
        (void)ui_kit_guide_card_title(
            canvas, (uint8_t)y, guide->icon, guide->title, guide->short_title);
        return;
    }
    const int16_t icon_x = 6 + slide_px;
    const int16_t title_x = 22 + slide_px;
    if(icon_x >= 0 && icon_x <= 118)
        ui_kit_icon(canvas, guide->icon, icon_x, y + 1, 10U, false, false, 0U);
    if(title_x < 0 || title_x >= 126) return;
    canvas_set_color(canvas, ColorBlack);
    canvas_set_font(canvas, FontPrimary);
    uint16_t width = (uint16_t)(126 - title_x);
    if(width > 101U) width = 101U;
    (void)ui_kit_text(
        canvas, title_x, y + 11, (uint8_t)width,
        guide->title, guide->short_title);
}

void labmate_info_draw_guide_card_motion(
    Canvas* canvas, uint8_t index, int16_t scroll_px,
    int8_t slide_px, uint8_t fade_strength) {
    if(!canvas) return;
    const LabMateInfoGuide* guide = labmate_info_guide(index);
    if(!guide) return;
    const int16_t max_scroll = (int16_t)labmate_info_guide_max_scroll_steps(index) * 12;
    if(scroll_px < -1) scroll_px = -1;
    if(scroll_px > max_scroll + 1) scroll_px = max_scroll + 1;
    if(slide_px < -8) slide_px = -8;
    if(slide_px > 8) slide_px = 8;
    const int16_t scroll = scroll_px;
    ui_kit_back_title(canvas, "Tool guides", NULL, NULL);
    char position[14];
    /* Avoid printf/heap allocation in the display hot-path: 1..17 only. */
    const uint8_t count = (uint8_t)(index + 1U);
    if(count < 10U) {
        position[0] = (char)('0' + count);
        position[1] = '\0';
    } else {
        position[0] = '1';
        position[1] = (char)('0' + count - 10U);
        position[2] = '\0';
    }
    char* end = position;
    while(*end) ++end;
    const char suffix[] = " of 17";
    for(uint8_t i = 0U; i < sizeof(suffix); ++i) end[i] = suffix[i];
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str_aligned(canvas, 126, 9, AlignRight, AlignBottom, position);
    ui_kit_guide_progress(canvas, index, LABMATE_INFO_GUIDE_COUNT);

    /* Content is a virtual document below the fixed y0..13 header.
     * Each element is drawn only when ENTIRELY inside y14..63. Input scroll
     * animates between whole 12px stops without clipped glyphs. */
    const int16_t title_y = 15 - scroll;
    guide_card_title_shifted(canvas, title_y, guide, slide_px);
    guide_secondary_line(canvas, 35 - scroll, guide->summary[0], slide_px);
    guide_secondary_line(canvas, 43 - scroll, guide->summary[1], slide_px);

    for(uint8_t row = 0U; row < guide->chip_rows; ++row) {
        const int16_t top = 46 + row * 12 - scroll;
        if(top < 14 || top > 53) continue;
        const int16_t first_x = 6 + slide_px;
        if(first_x < 0) continue;
        uint16_t x = (uint16_t)first_x;
        canvas_set_font(canvas, FontSecondary);
        for(uint8_t item = 0U; item < LABMATE_INFO_GUIDE_PINS_PER_ROW; ++item) {
            const char* chip = guide->chips[row][item];
            if(!chip) break;
            const uint16_t width = canvas_string_width(canvas, chip) + 8U;
            if(x + width > 125U) break;
            (void)ui_kit_guide_pin_chip(canvas, (uint8_t)x, (uint8_t)top, chip);
            x += width + 5U;
        }
    }

    const uint16_t after_chips = 46U + (uint16_t)guide->chip_rows * 12U;
    for(uint8_t i = 0U; i < guide->fact_count; ++i) {
        guide_secondary_line(canvas,
                             (int16_t)(after_chips + 7U + i * 9U) - scroll,
                             guide->facts[i], slide_px);
    }
    const uint16_t control_first = after_chips + 9U * guide->fact_count + 2U;
    for(uint8_t i = 0U; i < guide->control_count; ++i) {
        const int16_t y = (int16_t)(control_first + i * 12U) - scroll;
        if(y < 14 || y > 54) continue;
        const int16_t key_x = 6 + slide_px;
        if(key_x >= 0 && key_x <= 118)
            (void)ui_kit_key_hint(canvas, (uint8_t)key_x, (uint8_t)y,
                                  guide->controls[i].key, guide->controls[i].label);
    }
    const uint16_t last_bottom = control_first +
                                 12U * (guide->control_count - 1U) + 10U;
    guide_dither_fade(canvas, fade_strength);
    ui_kit_guide_scroll_thumb(canvas, 14U, 50U,
                              (uint16_t)(last_bottom - 14U),
                              (uint16_t)(scroll < 0 ? 0 : scroll));
}

void labmate_info_draw_guide_card(Canvas* canvas, uint8_t index, uint8_t scroll_steps) {
    labmate_info_draw_guide_card_motion(
        canvas, index, (int16_t)scroll_steps * 12, 0, 0U);
}

/* Static QR: 29x29 modules + four-module quiet zone all around = 37x37.
 * Flipper cannot fit a 58x58 symbol plus its mandated quiet zone AND text.
 * Physical phone camera acceptance remains a separate user test. */
static void info_project_qr(Canvas* canvas, int8_t slide_px) {
    const int16_t shifted_x = 4 + slide_px;
    if(shifted_x < 0 || shifted_x > 91) return;
    const uint8_t x = (uint8_t)shifted_x;
    const uint8_t y = 19U;
    canvas_set_color(canvas, ColorWhite);
    canvas_draw_box(canvas, x, y, 37U, 37U);
    canvas_set_color(canvas, ColorBlack);
    for(uint8_t row = 0U; row < LABMATE_INFO_QR_SIDE; ++row) {
        for(uint8_t column = 0U; column < LABMATE_INFO_QR_SIDE; ++column) {
            const uint8_t value = labmate_info_qr[row][column >> 3U];
            if(value & (uint8_t)(0x80U >> (column & 7U))) {
                canvas_draw_dot(canvas, x + 4U + column, y + 4U + row);
            }
        }
    }
}

void labmate_info_draw_project_motion(
    Canvas* canvas, int8_t slide_px, uint8_t fade_strength) {
    if(!canvas) return;
    ui_kit_back_title(canvas, "Project", NULL, NULL);
    info_project_qr(canvas, slide_px);
    /* Each string is checked before painting. The exact full URL is in the QR;
     * these human-readable parts use the 84px beside it without collisions. */
    (void)info_line_shifted(canvas, 44U, 19U, 83U, "Source and", slide_px);
    (void)info_line_shifted(canvas, 44U, 27U, 83U, "releases", slide_px);
    (void)info_line_shifted(canvas, 44U, 36U, 83U, "Scan on phone", slide_px);
    (void)info_line_shifted(canvas, 44U, 45U, 83U, "flipper-labmate", slide_px);
    (void)info_line_shifted(canvas, 44U, 54U, 83U, "github.com/", slide_px);
    (void)info_line_shifted(canvas, 44U, 63U, 83U, "sehmusadsoy-ui", slide_px);
    guide_dither_fade(canvas, fade_strength);
}

void labmate_info_draw_project(Canvas* canvas) {
    labmate_info_draw_project_motion(canvas, 0, 0U);
}

static void info_safety_pin(Canvas* canvas, int8_t slide_px) {
    const int16_t start_x = 6 + slide_px;
    if(start_x < 0 || start_x > 114) return;
    /* A 14x14 procedural GPIO-pin sketch; no alert triangle or bitmap. */
    canvas_draw_rframe(canvas, start_x, 14U, 14U, 14U, 3U);
    canvas_draw_line(canvas, 10 + slide_px, 18, 10 + slide_px, 23);
    canvas_draw_line(canvas, 15 + slide_px, 18, 15 + slide_px, 23);
    canvas_draw_line(canvas, 10 + slide_px, 18, 15 + slide_px, 18);
    canvas_draw_dot(canvas, 12 + slide_px, 21);
    canvas_draw_line(canvas, 11 + slide_px, 27, 11 + slide_px, 30);
    canvas_draw_line(canvas, 15 + slide_px, 27, 15 + slide_px, 30);
}

void labmate_info_draw_safety_motion(
    Canvas* canvas, uint8_t detail_page, int8_t slide_px, uint8_t fade_strength) {
    if(!canvas) return;
    ui_kit_back_title(canvas, "Safety", NULL, NULL);
    info_safety_pin(canvas, slide_px);
    canvas_set_font(canvas, FontPrimary);
    const int16_t title_x = 27 + slide_px;
    if(title_x >= 0 && title_x <= 125) {
        uint16_t width = (uint16_t)(126 - title_x);
        if(width > 98U) width = 98U;
        (void)ui_kit_text(canvas, title_x, 25U, (uint8_t)width, "3.3 V only", NULL);
    }
    if(detail_page == 0U) {
        /* Verbatim user-approved safety sentence, split into two lines. */
        (void)info_line_shifted(canvas, 5U, 40U, 121U, "Never connect 5 V or", slide_px);
        (void)info_line_shifted(canvas, 5U, 50U, 121U, "mains to the GPIO pins.", slide_px);
        const int16_t key_x = 5 + slide_px;
        if(key_x >= 0 && key_x <= 114)
            (void)ui_kit_key_hint(canvas, (uint8_t)key_x, 54U, UiKitKeyDown, "More");
    } else {
        /* Retained warning content from the existing README, not new advice. */
        (void)info_line_shifted(canvas, 5U, 37U, 121U, "Unknown voltage and", slide_px);
        (void)info_line_shifted(canvas, 5U, 46U, 121U, "automotive signals:", slide_px);
        (void)info_line_shifted(canvas, 5U, 55U, 121U, "never connect directly.", slide_px);
        (void)info_line_shifted(canvas, 5U, 63U, 121U, "Use verified signals.", slide_px);
    }
    guide_dither_fade(canvas, fade_strength);
}

void labmate_info_draw_safety(Canvas* canvas, uint8_t detail_page) {
    labmate_info_draw_safety_motion(canvas, detail_page, 0, 0U);
}
