#include "ui_kit.h"
#include "labmate_icon_gear_outline.h"
#include "labmate_icon_categories_outline.h"

/* Every draw starts in black and ends in black, regardless of inversion. */
static bool ui_kit_rect(int16_t x, int16_t y, uint8_t w, uint8_t h) {
    return w && h && x >= 0 && y >= 0 && x + w <= 128 && y + h <= 64;
}

uint16_t ui_kit_ease(uint8_t frame, uint8_t total) {
    if(!total || frame >= total) return 256U;
    const uint32_t left = 256U - (uint32_t)frame * 256U / total;
    return (uint16_t)(256U - (left * left * left) / 65536U);
}

int16_t ui_kit_lerp(int16_t from, int16_t to, uint8_t frame, uint8_t total) {
    const int32_t delta = (int32_t)to - from;
    return (int16_t)(from + (delta * ui_kit_ease(frame, total)) / 256);
}

bool ui_kit_text(
    Canvas* canvas, int16_t x, int16_t baseline, uint8_t width,
    const char* label, const char* short_label) {
    if(!canvas || !label || !width || x < 0 || baseline < 0 || baseline >= 64 ||
       x + width > 128) return false;
    const char* fitted = label;
    if(canvas_string_width(canvas, fitted) > width) fitted = short_label;
    if(!fitted || canvas_string_width(canvas, fitted) > width) return false;
    canvas_draw_str(canvas, x, baseline, fitted);
    return true;
}

void ui_kit_center_text(
    Canvas* canvas, uint8_t baseline, const char* label, const char* short_label) {
    if(!canvas || !label || baseline >= 64U) return;
    const char* fitted = label;
    if(canvas_string_width(canvas, fitted) > 120U) fitted = short_label;
    if(!fitted) return;
    const uint16_t width = canvas_string_width(canvas, fitted);
    if(width > 120U) return;
    canvas_draw_str(canvas, (128U - width) / 2U, baseline, fitted);
}

/* Light native header; reserve right edge for the version in the same font.
 * Measure both strings so they cannot collide on the 128px canvas. */
void ui_kit_brand(Canvas* c) {
    if(!c) return;
    canvas_set_color(c, ColorBlack);
    canvas_set_font(c, FontSecondary);
    const char* version = "V2.0";
    const uint16_t version_width = canvas_string_width(c, version);
    if(version_width > 116U) return;
    const uint8_t title_width = (uint8_t)(116U - version_width);
    (void)ui_kit_text(c, 4, 8, title_width, "LabMate Ultimate", "LabMate");
    canvas_draw_str(c, 124U - version_width, 8, version);
}

/* Draw the existing 10px app icon's distinctive pulse silhouette with lines,
 * at 2x size for the splash screen. No bitmap buffer or extra decoration. */
void ui_kit_splash_logo(Canvas* c, uint8_t x, uint8_t y) {
    if(!c || !ui_kit_rect(x,y,19,13)) return;
    canvas_set_color(c, ColorBlack);
    canvas_draw_line(c,x,y+12,x+4,y+12);
    canvas_draw_line(c,x+4,y+12,x+4,y+4);
    canvas_draw_line(c,x+4,y+4,x+10,y+4);
    canvas_draw_line(c,x+10,y+4,x+10,y+12);
    canvas_draw_line(c,x+10,y+12,x+14,y+12);
    canvas_draw_line(c,x+14,y+12,x+14,y+8);
    canvas_draw_line(c,x+14,y+8,x+18,y+8);
}

void ui_kit_carousel_card(
    Canvas* c, uint8_t x, uint8_t y, uint8_t w, uint8_t h, bool selected) {
    if(!c || !ui_kit_rect(x,y,w,h) || w < 7U || h < 7U) return;
    if(!selected) return;
    canvas_set_color(c, ColorBlack);
    canvas_draw_line(c, x+1, y+3, x+1, y+h-4);
    canvas_draw_line(c, x+w-2, y+3, x+w-2, y+h-4);
}
/* 0..8 icon coordinates are scaled into a fixed 1px margin. No bitmap data
 * or enlarged 2px strokes: all sizes use line/dot/box canvas primitives. */
static int16_t p(int16_t origin, uint8_t size, uint8_t coordinate) {
    return origin + 1 + ((uint16_t)coordinate * (size - 3U) + 4U) / 8U;
}

static void line(Canvas* c, int16_t x, int16_t y, uint8_t s,
                 uint8_t x1, uint8_t y1, uint8_t x2, uint8_t y2) {
    canvas_draw_line(c, p(x, s, x1), p(y, s, y1), p(x, s, x2), p(y, s, y2));
}

static void dot(Canvas* c, int16_t x, int16_t y, uint8_t s,
                uint8_t px, uint8_t py) {
    canvas_draw_dot(c, p(x, s, px), p(y, s, py));
}

/* Draw only the literal approved XBM bits. Never scale, interpolate,
 * rotate, smooth or write to the original bitmap arrays. A 12px slot
 * centers the 10px drawing; intermediate carousel sizes select 14px. */
static void ui_kit_gear_bitmap(
    Canvas* c, int16_t x, int16_t y, uint8_t slot_size) {
    const uint8_t glyph_size =
        slot_size >= 24U ? ICON_GEAR_24_W :
        slot_size >= 14U ? ICON_GEAR_14_W : ICON_GEAR_10_W;
    const uint8_t* bits =
        glyph_size == ICON_GEAR_24_W ? icon_gear_24 :
        glyph_size == ICON_GEAR_14_W ? icon_gear_14 : icon_gear_10;
    const uint8_t bytes_per_row = (glyph_size + 7U) / 8U;
    const int16_t left = x + (slot_size - glyph_size) / 2;
    const int16_t top = y + (slot_size - glyph_size) / 2;
    for(uint8_t yy = 0U; yy < glyph_size; ++yy) {
        for(uint8_t xx = 0U; xx < glyph_size; ++xx) {
            if(bits[yy * bytes_per_row + xx / 8U] & (uint8_t)(1U << (xx & 7U)))
                canvas_draw_dot(c, left + xx, top + yy);
        }
    }
}

/* Four new carousel drawings use the same discrete, unscaled bitmap sizes as
 * the locked Settings gear. They are separate from the existing tool icons. */
static void ui_kit_category_bitmap(
    Canvas* c, UiKitIcon icon, int16_t x, int16_t y, uint8_t slot_size) {
    const uint8_t glyph_size = slot_size >= 24U ? 24U : slot_size >= 14U ? 14U : 10U;
    const uint8_t* bits = NULL;
    switch(icon) {
    case UiKitIconCategoryMeasure:
        bits = glyph_size == 24U ? icon_category_measure_24 :
               glyph_size == 14U ? icon_category_measure_14 : icon_category_measure_10;
        break;
    case UiKitIconCategoryOutput:
        bits = glyph_size == 24U ? icon_category_output_24 :
               glyph_size == 14U ? icon_category_output_14 : icon_category_output_10;
        break;
    case UiKitIconCategoryRecords:
        bits = glyph_size == 24U ? icon_category_records_24 :
               glyph_size == 14U ? icon_category_records_14 : icon_category_records_10;
        break;
    case UiKitIconCategoryComm:
        bits = glyph_size == 24U ? icon_category_comm_24 :
               glyph_size == 14U ? icon_category_comm_14 : icon_category_comm_10;
        break;
    default: return;
    }
    const int16_t left = x + (slot_size - glyph_size) / 2;
    const int16_t top = y + (slot_size - glyph_size) / 2;
    const uint8_t stride = (glyph_size + 7U) / 8U;
    for(uint8_t yy = 0U; yy < glyph_size; ++yy) {
        for(uint8_t xx = 0U; xx < glyph_size; ++xx) {
            if(bits[yy * stride + xx / 8U] & (uint8_t)(1U << (xx & 7U)))
                canvas_draw_dot(c, left + xx, top + yy);
        }
    }
}

void ui_kit_icon(
    Canvas* c, UiKitIcon icon, int16_t x, int16_t y,
    uint8_t size, bool subdued, bool inverse, uint8_t phase) {
    if(!c || icon >= UiKitIconCount || size < 10U || size > 24U ||
       !ui_kit_rect(x, y, size, size)) return;
    canvas_set_color(c, inverse ? ColorWhite : ColorBlack);
    switch(icon) {
    case UiKitIconGpio:
        line(c,x,y,size,1,2,7,2); line(c,x,y,size,1,6,7,6);
        line(c,x,y,size,2,1,2,7); line(c,x,y,size,6,1,6,7);
        dot(c,x,y,size,4,4); line(c,x,y,size,0,4,2,4); line(c,x,y,size,6,4,8,4);
        break;
    case UiKitIconFreq:
        line(c,x,y,size,0,4,1,4); line(c,x,y,size,1,4,3,1);
        line(c,x,y,size,3,1,5,7); line(c,x,y,size,5,7,7,4);
        line(c,x,y,size,7,4,8,4);
        if(phase & 1U) dot(c,x,y,size,2,3);
        break;
    case UiKitIconPwm:
        line(c,x,y,size,0,6,2,6); line(c,x,y,size,2,6,2,2);
        line(c,x,y,size,2,2,6,2); line(c,x,y,size,6,2,6,6);
        line(c,x,y,size,6,6,8,6);
        if(phase & 1U) dot(c,x,y,size,4,4);
        break;
    case UiKitIconUart:
        line(c,x,y,size,0,2,7,2); line(c,x,y,size,7,2,5,0);
        line(c,x,y,size,7,2,5,4); line(c,x,y,size,8,6,1,6);
        line(c,x,y,size,1,6,3,4); line(c,x,y,size,1,6,3,8);
        break;
    case UiKitIconI2c:
        line(c,x,y,size,0,2,8,2); line(c,x,y,size,0,6,8,6);
        line(c,x,y,size,2,0,2,8); line(c,x,y,size,6,0,6,8);
        dot(c,x,y,size,4,4);
        break;
    case UiKitIconScope:
        line(c,x,y,size,0,0,8,0); line(c,x,y,size,0,8,8,8);
        line(c,x,y,size,0,0,0,8); line(c,x,y,size,8,0,8,8);
        line(c,x,y,size,1,5,3,5); line(c,x,y,size,3,5,3,2);
        line(c,x,y,size,3,2,5,2); line(c,x,y,size,5,2,5,6);
        line(c,x,y,size,5,6,7,6);
        break;
    case UiKitIconDoctor:
        line(c,x,y,size,4,0,4,8); line(c,x,y,size,0,4,8,4);
        line(c,x,y,size,2,2,6,2); line(c,x,y,size,2,6,6,6);
        break;
    case UiKitIconDash:
        line(c,x,y,size,0,8,8,8); line(c,x,y,size,1,6,1,7);
        line(c,x,y,size,3,4,3,7); line(c,x,y,size,5,1,5,7);
        line(c,x,y,size,7,3,7,7);
        break;
    case UiKitIconRec:
        line(c,x,y,size,1,0,7,0); line(c,x,y,size,1,0,1,8);
        line(c,x,y,size,7,0,7,8); line(c,x,y,size,1,8,7,8);
        line(c,x,y,size,3,1,3,3); line(c,x,y,size,3,3,6,3);
        dot(c,x,y,size,4,6);
        break;
    case UiKitIconInfo:
        line(c,x,y,size,2,0,6,0); line(c,x,y,size,1,1,1,7);
        line(c,x,y,size,7,1,7,7); line(c,x,y,size,2,8,6,8);
        dot(c,x,y,size,4,2); line(c,x,y,size,4,4,4,6);
        break;
    case UiKitIconSettings:
        ui_kit_gear_bitmap(c, x, y, size);
        break;
    case UiKitIconCategoryMeasure:
    case UiKitIconCategoryOutput:
    case UiKitIconCategoryRecords:
    case UiKitIconCategoryComm:
        ui_kit_category_bitmap(c, icon, x, y, size);
        break;
    default: break;
    }
    if(subdued && !inverse) {
        /* Only one in four stroke pixels is erased: neighbours stay clear. */
        canvas_set_color(c, ColorWhite);
        for(uint8_t yy = 0; yy < size; ++yy)
            for(uint8_t xx = (uint8_t)((4U - (yy & 3U)) & 3U); xx < size; xx += 4U)
                canvas_draw_dot(c, x + xx, y + yy);
    }
    canvas_set_color(c, ColorBlack);
}

void ui_kit_pulse_line(
    Canvas* c, uint8_t x, uint8_t y, uint8_t width,
    uint8_t phase, bool live) {
    if(!c || width < 12U || y < 3U || !ui_kit_rect(x, y-3U, width, 7U)) return;
    canvas_set_color(c, ColorBlack);
    if(!live) {
        canvas_draw_line(c, x, y, x + width - 1U, y);
        return;
    }
    const uint8_t start = x + 3U + (uint32_t)(width - 12U) * phase / 255U;
    canvas_draw_line(c, x, y, start, y);
    canvas_draw_line(c, start, y, start + 2U, y - 3U);
    canvas_draw_line(c, start + 2U, y - 3U, start + 5U, y + 3U);
    canvas_draw_line(c, start + 5U, y + 3U, start + 7U, y);
    canvas_draw_line(c, start + 7U, y, x + width - 1U, y);
}

void ui_kit_page_dots(Canvas* c, uint8_t current, uint8_t count) {
    if(!c || !count || count > 7U) return;
    const uint8_t left = (uint8_t)(64U - (count * 8U - 2U) / 2U);
    canvas_set_color(c, ColorBlack);
    for(uint8_t i = 0; i < count; ++i) {
        if(i == current) canvas_draw_box(c, left + i * 8U, 58, 3, 3);
        else canvas_draw_line(c, left + i * 8U, 59, left + i * 8U + 2U, 59);
    }
}

void ui_kit_pill(Canvas* c, uint8_t x, uint8_t y, uint8_t w, uint8_t h) {
    if(!c || !ui_kit_rect(x,y,w,h) || w < 7U || h < 7U) return;
    canvas_set_color(c, ColorBlack);
    canvas_draw_rbox(c, x, y, w, h, 3);
}

void ui_kit_panel(Canvas* c, uint8_t x, uint8_t y, uint8_t w, uint8_t h) {
    if(!c || !ui_kit_rect(x,y,w,h) || w < 7U || h < 7U) return;
    canvas_set_color(c, ColorWhite);
    canvas_draw_rbox(c, x, y, w, h, 3);
    canvas_set_color(c, ColorBlack);
    canvas_draw_rframe(c, x, y, w, h, 3);
}

void ui_kit_confirmation_choice(
    Canvas* c, const char* question, const char* short_question,
    const char* action, bool confirm_selected) {
    if(!c || !question || !action) return;
    ui_kit_dither(c, 0, 0, 128, 64);
    ui_kit_panel(c, 9, 14, 110, 38);
    canvas_set_font(c, FontSecondary);
    canvas_set_color(c, ColorBlack);
    (void)ui_kit_text(c, 17, 27, 95, question, short_question);
    if(confirm_selected) canvas_draw_rframe(c, 17, 35, 45, 12, 3);
    else ui_kit_pill(c, 17, 35, 45, 12);
    canvas_set_color(c, confirm_selected ? ColorBlack : ColorWhite);
    (void)ui_kit_text(c, 20, 44, 39, "Cancel", "Back");
    canvas_set_color(c, ColorBlack);
    if(confirm_selected) ui_kit_pill(c, 66, 35, 45, 12);
    else canvas_draw_rframe(c, 66, 35, 45, 12, 3);
    canvas_set_color(c, confirm_selected ? ColorWhite : ColorBlack);
    (void)ui_kit_text(c, 70, 44, 38, action, "OK");
    canvas_set_color(c, ColorBlack);
}

void ui_kit_confirmation(
    Canvas* c, const char* question, const char* short_question,
    const char* action) {
    ui_kit_confirmation_choice(c, question, short_question, action, true);
}

void ui_kit_back_title(Canvas* c, const char* name, const char* short_name, const char* pin) {
    if(!c) return;
    canvas_set_color(c, ColorBlack);
    canvas_set_font(c, FontSecondary);
    canvas_draw_line(c, 7, 2, 4, 5);
    canvas_draw_line(c, 4, 5, 7, 8);
    (void)ui_kit_text(c, 12, 9, pin ? 83U : 111U, name, short_name);
    if(pin) {
        canvas_draw_rframe(c, 99, 0, 27, 11, 3);
        (void)ui_kit_text(c, 103, 8, 20, pin, NULL);
    }
}

void ui_kit_list_row(
    Canvas* c, uint8_t y, UiKitIcon icon, const char* title,
    const char* short_title, bool inverse) {
    if(!c || y > 54U) return;
    canvas_set_color(c, inverse ? ColorWhite : ColorBlack);
    ui_kit_icon(c, icon, 6, y + 2U, 10, false, inverse, 0U);
    canvas_set_color(c, inverse ? ColorWhite : ColorBlack);
    canvas_set_font(c, FontSecondary);
    (void)ui_kit_text(c, 22, y + 10U, 91U, title, short_title);
    canvas_draw_line(c, 118, y + 5U, 121, y + 7U);
    canvas_draw_line(c, 121, y + 7U, 118, y + 9U);
    canvas_set_color(c, ColorBlack);
}

void ui_kit_dither(Canvas* c, uint8_t x, uint8_t y, uint8_t w, uint8_t h) {
    if(!c || !ui_kit_rect(x,y,w,h)) return;
    canvas_set_color(c, ColorBlack);
    for(uint8_t yy = y; yy < (uint8_t)(y+h); yy += 2U)
        for(uint8_t xx = x + (yy & 2U ? 1U : 0U); xx < (uint8_t)(x+w); xx += 2U)
            canvas_draw_dot(c, xx, yy);
}

void ui_kit_sparkline(
    Canvas* c, const uint8_t* samples, uint8_t count,
    uint8_t x, uint8_t y, uint8_t width, uint8_t height) {
    if(!c || !samples || !count || height < 2 || width < 2 ||
       !ui_kit_rect(x,y,width,height)) return;
    canvas_set_color(c, ColorBlack);
    if(count == 1U) {
        canvas_draw_dot(c, x, y + height - 1U - (uint16_t)samples[0]*(height-1U)/255U);
        return;
    }
    for(uint8_t i = 1; i < count; ++i) {
        const uint8_t a = (uint8_t)(x + (uint32_t)(i-1U)*(width-1U)/(count-1U));
        const uint8_t b = (uint8_t)(x + (uint32_t)i*(width-1U)/(count-1U));
        const uint8_t ya = (uint8_t)(y + height-1U - (uint16_t)samples[i-1U]*(height-1U)/255U);
        const uint8_t yb = (uint8_t)(y + height-1U - (uint16_t)samples[i]*(height-1U)/255U);
        canvas_draw_line(c,a,ya,b,yb);
    }
}

/* Doctor Step 1: fixed-height settings row. All previous primitives above
 * stay unchanged so Polish07 continues to render identically. */
bool ui_kit_settings_row(
    Canvas* c, uint8_t y, const char* label, const char* value,
    UiKitSettingsRowState state) {
    if(!c || !label || !value ||
       (unsigned)state > (unsigned)UiKitSettingsDisabled ||
       !ui_kit_rect(2, y, 124, 13)) return false;

    canvas_set_font(c, FontSecondary);
    const uint16_t label_w = canvas_string_width(c, label);
    const uint16_t value_w = canvas_string_width(c, value);
    const bool editing = state == UiKitSettingsEditing;
    const int32_t value_right = editing ? 111 : 121;
    const int32_t value_x = value_right - value_w;
    const int32_t leftmost_value = editing ? value_x - 8 : value_x;
    /* Both strings are atomic: reject long content before painting a pill. */
    if(label_w == 0 || value_w == 0 ||
       6 + label_w + 4 > leftmost_value || value_right > 121 ||
       (editing && value_x < 8)) return false;

    const bool inverse = state == UiKitSettingsSelected || editing;
    if(inverse) ui_kit_pill(c, 2, y, 124, 13);
    canvas_set_color(c, inverse ? ColorWhite : ColorBlack);
    canvas_draw_str(c, 6, y + 9, label);
    canvas_draw_str(c, value_x, y + 9, value);
    if(editing) {
        /* Compact chevrons fit inside the selected pill; no unsupported
         * special-arrow font glyphs are used. */
        canvas_draw_line(c, value_x - 5, y + 4, value_x - 8, y + 6);
        canvas_draw_line(c, value_x - 8, y + 6, value_x - 5, y + 8);
        canvas_draw_line(c, 115, y + 4, 118, y + 6);
        canvas_draw_line(c, 118, y + 6, 115, y + 8);
    }
    if(state == UiKitSettingsDisabled) {
        /* A 1-bit checker erases alternate ink pixels, never draws gray. */
        canvas_set_color(c, ColorWhite);
        for(uint8_t yy = y + 2; yy <= (uint8_t)(y + 10); ++yy)
            for(uint8_t xx = 6 + (yy & 1U); xx < 122U; xx += 2U)
                canvas_draw_dot(c, xx, yy);
    }
    canvas_set_color(c, ColorBlack);
    return true;
}

void ui_kit_toggle(
    Canvas* c, uint8_t x, uint8_t y, bool on,
    bool inverse, uint8_t frame) {
    if(!c || !ui_kit_rect(x, y, 18, 9)) return;
    if(frame > 4U) frame = 4U;
    /* Four non-blocking ease-out frames move the 5px knob by 9px. */
    const uint8_t position = on ? frame : (uint8_t)(4U - frame);
    const uint8_t knob_x = (uint8_t)(x + 2U +
        (9U * ui_kit_ease(position, 4U) + 128U) / 256U);
    const bool filled = on ? frame >= 2U : frame < 2U;
    canvas_set_color(c, inverse ? ColorWhite : ColorBlack);
    if(filled) canvas_draw_rbox(c, x, y, 18, 9, 4);
    else canvas_draw_rframe(c, x, y, 18, 9, 4);
    canvas_set_color(c, filled ? (inverse ? ColorBlack : ColorWhite) :
                                (inverse ? ColorWhite : ColorBlack));
    canvas_draw_rbox(c, knob_x, y + 2U, 5, 5, 2);
    canvas_set_color(c, ColorBlack);
}

bool ui_kit_settings_option_row(
    Canvas* c, uint8_t y, const char* label, const char* value,
    UiKitSettingsOptionKind kind, bool inverse, bool switch_on,
    uint8_t switch_frame) {
    if(!c || !label || kind > UiKitSettingsOptionDestructive ||
       !ui_kit_rect(2, y, 124, 13)) return false;
    canvas_set_font(c, FontSecondary);
    const uint16_t label_width = canvas_string_width(c, label);
    int16_t right_edge = 118;
    if(kind == UiKitSettingsOptionToggle) right_edge = 97;
    if(kind == UiKitSettingsOptionDestructive) right_edge = 122;
    if(!label_width || (uint16_t)(6U + label_width) > (uint16_t)right_edge)
        return false;
    const uint16_t value_width =
        kind == UiKitSettingsOptionValue && value ? canvas_string_width(c, value) : 0U;
    if(kind == UiKitSettingsOptionValue &&
       (!value || !value_width || (int32_t)(6U + label_width + 5U + value_width) > 118))
        return false;

    canvas_set_color(c, inverse ? ColorWhite : ColorBlack);
    canvas_draw_str(c, 6, y + 9U, label);
    if(kind == UiKitSettingsOptionValue) {
        canvas_draw_str(c, 118 - value_width, y + 9U, value);
    }
    if(kind == UiKitSettingsOptionValue || kind == UiKitSettingsOptionLink) {
        canvas_draw_line(c, 120, y + 4U, 123, y + 6U);
        canvas_draw_line(c, 123, y + 6U, 120, y + 8U);
    } else if(kind == UiKitSettingsOptionToggle) {
        ui_kit_toggle(c, 102U, y + 2U, switch_on, inverse, switch_frame);
    } else if(kind == UiKitSettingsOptionDestructive && !inverse) {
        /* Quiet visual distinction without a red color or alert triangle. */
        canvas_draw_line(c, 6, y + 11U, 6 + label_width - 1U, y + 11U);
    }
    canvas_set_color(c, ColorBlack);
    return true;
}

void ui_kit_toast(Canvas* c, const char* text, uint8_t progress) {
    if(!c || !text || progress == 0U) return;
    canvas_set_font(c, FontSecondary);
    const uint16_t word_width = canvas_string_width(c, text);
    if(!word_width || word_width > 87U) return;
    const uint8_t box_width = (uint8_t)(word_width + 26U);
    const uint8_t box_x = (uint8_t)((128U - box_width) / 2U);
    const uint8_t box_y = (uint8_t)(64U - ((uint16_t)progress * 16U + 254U) / 255U);
    const uint8_t visible_height = (uint8_t)(64U - box_y);
    if(visible_height < 3U) return;
    /* Erase half the bottom-row ink outside the floating toast as well:
     * the list remains in place, gently subdued behind the overlay. */
    canvas_set_color(c, ColorWhite);
    for(uint8_t yy = box_y; yy < 64U; ++yy)
        for(uint8_t xx = (uint8_t)(2U + (yy & 1U));
            xx < 126U; xx += 2U)
            canvas_draw_dot(c, xx, yy);
    ui_kit_panel(c, box_x, box_y, box_width,
                 visible_height < 16U ? visible_height : 16U);
    if(visible_height >= 15U) {
        canvas_set_color(c, ColorBlack);
        const uint8_t check_x = (uint8_t)(box_x + 7U);
        canvas_draw_line(c, check_x, box_y + 8U, check_x + 2U, box_y + 10U);
        canvas_draw_line(c, check_x + 2U, box_y + 10U, check_x + 6U, box_y + 5U);
        canvas_draw_str(c, box_x + 17U, box_y + 11U, text);
    }
    canvas_set_color(c, ColorBlack);
}

void ui_kit_confirmation_details(
    Canvas* c, bool confirm_selected,
    const char* line_one, const char* line_two, const char* line_three) {
    if(!c || !line_one || !line_two || !line_three) return;
    canvas_set_font(c, FontSecondary);
    /* Preflight before dimming or drawing a panel. */
    const char* title = "Reset interface?";
    if(canvas_string_width(c, title) > 108U ||
       canvas_string_width(c, line_one) > 108U ||
       canvas_string_width(c, line_two) > 108U ||
       canvas_string_width(c, line_three) > 108U) return;
    ui_kit_dither(c, 0, 0, 128, 64);
    ui_kit_panel(c, 5U, 9U, 118U, 55U);
    canvas_set_font(c, FontSecondary);
    canvas_set_color(c, ColorBlack);
    (void)ui_kit_text(c, 11, 19, 108, title, NULL);
    (void)ui_kit_text(c, 11, 31, 108, line_one, NULL);
    (void)ui_kit_text(c, 11, 39, 108, line_two, NULL);
    (void)ui_kit_text(c, 11, 47, 108, line_three, NULL);
    if(!confirm_selected) ui_kit_pill(c, 14U, 52U, 46U, 11U);
    else canvas_draw_rframe(c, 14U, 52U, 46U, 11U, 3U);
    canvas_set_color(c, confirm_selected ? ColorBlack : ColorWhite);
    (void)ui_kit_text(c, 22U, 60U, 36U, "Cancel", NULL);
    canvas_set_color(c, ColorBlack);
    if(confirm_selected) ui_kit_pill(c, 68U, 52U, 46U, 11U);
    else canvas_draw_rframe(c, 68U, 52U, 46U, 11U, 3U);
    canvas_set_color(c, confirm_selected ? ColorWhite : ColorBlack);
    (void)ui_kit_text(c, 79U, 60U, 32U, "Reset", NULL);
    canvas_set_color(c, ColorBlack);
}

void ui_kit_diag_glyph(Canvas* c, uint8_t x, uint8_t y, UiKitDiagKind kind) {
    if(!c || kind >= UiKitDiagCount || !ui_kit_rect(x, y, 24, 10)) return;
    canvas_set_color(c, ColorBlack);
    /* Direct procedural strokes (no bitmap, heap buffer or glyph table). */
#define D(a,b,d,e) canvas_draw_line(c, x + (a), y + (b), x + (d), y + (e))
    switch(kind) {
    case UiKitDiagNoData:
        D(0,5,23,5);
        break;
    case UiKitDiagStuckHigh:
        D(0,1,23,1);
        break;
    case UiKitDiagStuckLow:
        D(0,8,23,8);
        break;
    case UiKitDiagMissingPulse:
        D(0,7,3,7); D(3,7,3,2); D(3,2,8,2); D(8,2,8,7);
        D(8,7,19,7); D(19,7,19,2); D(19,2,22,2); D(22,2,22,7);
        D(22,7,23,7);
        break;
    case UiKitDiagRuntPulses:
        D(0,7,3,7); D(3,7,3,2); D(3,2,7,2); D(7,2,7,7);
        D(7,7,12,7); D(12,7,12,5); D(12,5,14,5); D(14,5,14,7);
        D(14,7,20,7); D(20,7,20,2); D(20,2,23,2);
        break;
    case UiKitDiagJitter:
        D(0,7,2,7); D(2,7,2,2); D(2,2,7,2); D(7,2,7,7);
        D(7,7,12,7); D(12,7,12,2); D(12,2,15,2); D(15,2,15,7);
        D(15,7,20,7); D(20,7,20,2); D(20,2,23,2);
        break;
    case UiKitDiagBounce:
        D(0,7,4,7); D(4,7,4,2); D(4,2,6,2); D(6,2,6,6);
        D(6,6,7,6); D(7,6,7,3); D(7,3,8,3); D(8,3,8,7);
        D(8,7,15,7); D(15,7,15,2); D(15,2,20,2);
        D(20,2,20,7); D(20,7,23,7);
        break;
    case UiKitDiagOffFrequencyDuty:
        /* Dashed expected guide plus shifted duty/timing waveform. */
        for(uint8_t i = 0; i < 24; i += 2U) canvas_draw_dot(c, x + i, y + 5);
        D(0,7,2,7); D(2,7,2,3); D(2,3,9,3); D(9,3,9,7);
        D(9,7,15,7); D(15,7,15,3); D(15,3,20,3); D(20,3,20,7);
        D(20,7,23,7);
        break;
    case UiKitDiagHealthy:
        D(0,7,3,7); D(3,7,3,2); D(3,2,8,2); D(8,2,8,7);
        D(8,7,13,7); D(13,7,13,2); D(13,2,18,2); D(18,2,18,7);
        D(18,7,23,7);
        break;
    default: break;
    }
#undef D
    canvas_set_color(c, ColorBlack);
}

/* Accept a full label or only its explicit short alternative. Caller retains
 * control of terminology; never clip glyphs or silently abbreviate. */
static const char* ui_kit_result_fit(
    Canvas* c, const char* full, const char* short_text, uint16_t width) {
    if(!full) return NULL;
    if(canvas_string_width(c, full) <= width) return full;
    if(short_text && canvas_string_width(c, short_text) <= width)
        return short_text;
    return NULL;
}

bool ui_kit_result_card(Canvas* c, const UiKitResultCard* card) {
    if(!c || !card || card->glyph >= UiKitDiagCount || !card->verdict ||
       !card->reason || !card->action) return false;

    /* Check every string in its actual font BEFORE drawing any pixels. */
    canvas_set_font(c, FontPrimary);
    const char* verdict = ui_kit_result_fit(
        c, card->verdict, card->short_verdict, 120U);
    canvas_set_font(c, FontSecondary);
    const char* why = ui_kit_result_fit(
        c, card->reason, card->short_reason, 120U);
    const bool second = card->reason_second && card->reason_second[0] != '\0';
    const char* why_second = second ? ui_kit_result_fit(
        c, card->reason_second, card->short_reason_second, 120U) : NULL;
    const uint16_t action_max = card->advisory ? 63U : 114U;
    const char* action = ui_kit_result_fit(
        c, card->action, card->short_action, action_max);
    const char* advisory = card->advisory ?
        ui_kit_result_fit(c, "Advisory", "Advice", 43U) : NULL;
    if(!verdict || !why || (second && !why_second) || !action ||
       (card->advisory && !advisory)) return false;

    const uint16_t action_w = canvas_string_width(c, action);
    const uint8_t chip_w = card->advisory ? 69U :
        (uint8_t)(action_w + 8U < 26U ? 26U : action_w + 8U);
    const uint8_t chip_x = card->advisory ? 57U : (uint8_t)(126U - chip_w);

    ui_kit_diag_glyph(c, 52, 12, card->glyph);
    canvas_set_color(c, ColorBlack);
    canvas_set_font(c, FontPrimary);
    canvas_draw_str(c, (128U - canvas_string_width(c, verdict)) / 2U, 36, verdict);
    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, (128U - canvas_string_width(c, why)) / 2U,
                    second ? 45 : 49, why);
    if(second)
        canvas_draw_str(c, (128U - canvas_string_width(c, why_second)) / 2U,
                        53, why_second);

    if(card->advisory) {
        canvas_draw_rframe(c, 2, 55, 51, 9, 3);
        canvas_draw_str(c, 6, 62, advisory);
    }
    ui_kit_pill(c, chip_x, 55, chip_w, 9);
    canvas_set_color(c, ColorWhite);
    canvas_draw_str(c, chip_x + 4, 62, action);
    canvas_set_color(c, ColorBlack);
    return true;
}

/* Info Step 1 is deliberately additive. All existing rendering calls above
 * retain exactly the same pixels and state; new components are unused until
 * the separately reviewed Info screen integration in Steps 2 and 3. */
static const char* ui_kit_guide_fitted(
    Canvas* c, const char* full, const char* short_name, uint16_t width) {
    if(!full || !full[0]) return NULL;
    if(canvas_string_width(c, full) <= width) return full;
    if(short_name && short_name[0] &&
       canvas_string_width(c, short_name) <= width) return short_name;
    return NULL;
}

static uint8_t ui_kit_key_width(UiKitKey key) {
    switch(key) {
    case UiKitKeyOk: return 15U;
    case UiKitKeyOkHold: return 17U;
    case UiKitKeyLeftRight:
    case UiKitKeyUpDown: return 16U;
    case UiKitKeyUp:
    case UiKitKeyDown: return 12U;
    case UiKitKeyBack: return 14U;
    default: return 0U;
    }
}

bool ui_kit_key_hint_at(
    Canvas* c, uint8_t x, uint8_t y, UiKitKey key, const char* label) {
    const uint8_t key_w = ui_kit_key_width(key);
    if(!c || !label || !key_w || !ui_kit_rect(x, y, key_w, 10U)) return false;

    canvas_set_font(c, FontSecondary);
    const uint16_t label_w = canvas_string_width(c, label);
    const uint16_t label_x = (uint16_t)x + key_w + 3U;
    if(label_x + label_w > 126U ||
       ((key == UiKitKeyOk || key == UiKitKeyOkHold) &&
        canvas_string_width(c, "OK") > key_w - 4U)) return false;

    canvas_set_color(c, ColorBlack);
    canvas_draw_rframe(c, x, y, key_w, 10U, 3U);
    switch(key) {
    case UiKitKeyOk:
    case UiKitKeyOkHold:
        /* Same native secondary glyph as other help labels, no bitmap. */
        canvas_draw_str(c, x + 2U, y + 7U, "OK");
        if(key == UiKitKeyOkHold)
            canvas_draw_line(c, x + 3U, y + 8U, x + key_w - 4U, y + 8U);
        break;
    case UiKitKeyLeftRight:
        canvas_draw_line(c, x + 6U, y + 2U, x + 3U, y + 4U);
        canvas_draw_line(c, x + 3U, y + 4U, x + 6U, y + 6U);
        canvas_draw_line(c, x + 9U, y + 2U, x + 12U, y + 4U);
        canvas_draw_line(c, x + 12U, y + 4U, x + 9U, y + 6U);
        break;
    case UiKitKeyUpDown:
        canvas_draw_line(c, x + 5U, y + 4U, x + 7U, y + 2U);
        canvas_draw_line(c, x + 7U, y + 2U, x + 9U, y + 4U);
        canvas_draw_line(c, x + 5U, y + 5U, x + 7U, y + 7U);
        canvas_draw_line(c, x + 7U, y + 7U, x + 9U, y + 5U);
        break;
    case UiKitKeyUp:
        canvas_draw_line(c, x + 3U, y + 6U, x + 5U, y + 3U);
        canvas_draw_line(c, x + 5U, y + 3U, x + 7U, y + 6U);
        break;
    case UiKitKeyDown:
        canvas_draw_line(c, x + 3U, y + 3U, x + 5U, y + 6U);
        canvas_draw_line(c, x + 5U, y + 6U, x + 7U, y + 3U);
        break;
    case UiKitKeyBack:
        canvas_draw_line(c, x + 7U, y + 2U, x + 4U, y + 5U);
        canvas_draw_line(c, x + 4U, y + 5U, x + 7U, y + 8U);
        canvas_draw_line(c, x + 4U, y + 5U, x + 10U, y + 5U);
        break;
    default: break;
    }
    if(label[0]) canvas_draw_str(c, label_x, y + 8U, label);
    canvas_set_color(c, ColorBlack);
    return true;
}

/* Pixel-target key hints for the redesigned GPIO/Counter screens. The old
 * generic y-position renderer above intentionally remains byte-for-byte
 * equivalent for Info/Doctor/Settings and other approved screens. */
static uint8_t ui_kit_compact_key_width(UiKitKey key) {
    switch(key) {
    case UiKitKeyLeftRight: return 18U;
    case UiKitKeyOk: return 19U;
    case UiKitKeyUp: return 16U;
    case UiKitKeyOkHold: return 21U;
    case UiKitKeyUpDown: return 18U;
    case UiKitKeyDown: return 16U;
    case UiKitKeyBack: return 16U;
    default: return 0U;
    }
}

uint8_t ui_kit_key_hint_compact(
    Canvas* c, uint8_t x, UiKitKey key, const char* label) {
    if(!c || !label) return 0U;
    const uint8_t width = ui_kit_compact_key_width(key);
    if(!width || !ui_kit_rect(x, 54U, width, 10U)) return 0U;
    canvas_set_font(c, FontSecondary);
    const uint16_t text_w = canvas_string_width(c, label);
    const uint16_t text_x = (uint16_t)x + width + 3U;
    const uint16_t end_x = text_x + text_w;
    if(end_x > 127U ||
       ((key == UiKitKeyOk || key == UiKitKeyOkHold) &&
        canvas_string_width(c, "OK") > (uint16_t)(width - 4U))) return 0U;

    canvas_set_color(c, ColorBlack);
    canvas_draw_rframe(c, x, 54U, width, 10U, 3U);
    switch(key) {
    case UiKitKeyLeftRight:
        /* 3x5 filled left/right triangles, one at each end of the chip. */
        for(uint8_t dy = 0U; dy < 5U; ++dy) {
            const uint8_t inset = dy <= 2U ? (uint8_t)(2U-dy) : (uint8_t)(dy-2U);
            canvas_draw_line(c, x+4U+inset, 56U+dy, x+6U, 56U+dy);
            canvas_draw_line(c, x+11U, 56U+dy, x+13U-inset, 56U+dy);
        }
        break;
    case UiKitKeyOk:
    case UiKitKeyOkHold: {
        const uint16_t ok_w = canvas_string_width(c, "OK");
        canvas_draw_str(c, x+(width-ok_w)/2U, 62U, "OK");
        if(key == UiKitKeyOkHold)
            canvas_draw_line(c, x+5U, 63U, x+width-6U, 63U);
        break;
    }
    case UiKitKeyUp:
        canvas_draw_dot(c, x+7U, 57U);
        canvas_draw_line(c, x+6U, 58U, x+8U, 58U);
        canvas_draw_line(c, x+5U, 59U, x+9U, 59U);
        break;
    case UiKitKeyDown:
        canvas_draw_line(c, x+5U, 57U, x+9U, 57U);
        canvas_draw_line(c, x+6U, 58U, x+8U, 58U);
        canvas_draw_dot(c, x+7U, 59U);
        break;
    case UiKitKeyUpDown:
        canvas_draw_line(c, x+7U, 56U, x+5U, 58U);
        canvas_draw_line(c, x+7U, 56U, x+9U, 58U);
        canvas_draw_line(c, x+5U, 60U, x+7U, 62U);
        canvas_draw_line(c, x+9U, 60U, x+7U, 62U);
        break;
    case UiKitKeyBack:
        canvas_draw_line(c, x+9U, 56U, x+5U, 59U);
        canvas_draw_line(c, x+5U, 59U, x+9U, 62U);
        break;
    default: break;
    }
    if(label[0]) canvas_draw_str(c, text_x, 62U, label);
    canvas_set_color(c, ColorBlack);
    return (uint8_t)end_x;
}

bool ui_kit_info_identity_card(Canvas* c, uint8_t y, uint8_t phase) {
    if(!c || y < 1U || !ui_kit_rect(4U, y, 120U, 28U)) return false;

    /* One additional physical pixel between letters, rather than an
     * alternate uppercase bitmap or unsupported custom font. */
    const char* subtitle = "ULTIMATE";
    canvas_set_font(c, FontPrimary);
    const uint16_t title_w = canvas_string_width(c, "LabMate");
    if(title_w > 116U) return false;
    canvas_set_font(c, FontSecondary);
    uint16_t subtitle_w = 0U;
    char ch[2] = {0, 0};
    for(uint8_t i = 0; subtitle[i]; ++i) {
        ch[0] = subtitle[i];
        subtitle_w += canvas_string_width(c, ch);
        if(subtitle[i + 1U]) subtitle_w++;
    }
    const uint16_t dev_w = canvas_string_width(c, "v2.0DEV");
    const uint16_t e11_w = canvas_string_width(c, "E11");
    const uint16_t version_w = dev_w + e11_w + 11U;
    if(subtitle_w > 116U || version_w > 104U) return false;

    /* Keep an unobstructed Pulse Line with a real gap to the version text. */
    const uint16_t version_x = 124U - version_w;
    if(version_x <= 25U) return false;
    const uint8_t line_w = (uint8_t)(version_x - 12U);
    if(line_w < 12U) return false;

    canvas_set_color(c, ColorBlack);
    canvas_set_font(c, FontPrimary);
    canvas_draw_str(c, (128U - title_w) / 2U, y + 10U, "LabMate");
    canvas_set_font(c, FontSecondary);
    uint16_t at = (128U - subtitle_w) / 2U;
    for(uint8_t i = 0; subtitle[i]; ++i) {
        ch[0] = subtitle[i];
        canvas_draw_str(c, at, y + 18U, ch);
        at += canvas_string_width(c, ch) + 1U;
    }
    canvas_draw_str(c, version_x, y + 26U, "v2.0DEV");
    canvas_draw_dot(c, version_x + dev_w + 5U, y + 23U);
    canvas_draw_str(c, version_x + dev_w + 11U, y + 26U, "E11");

    const uint8_t anim_phase = phase > UI_KIT_TWEEN_FRAMES ?
                                   UI_KIT_TWEEN_FRAMES : phase;
    const uint16_t amount = ui_kit_ease(anim_phase, UI_KIT_TWEEN_FRAMES);
    const uint8_t visible = (uint8_t)(1U + ((uint32_t)(line_w - 1U) * amount) / 256U);
    canvas_draw_line(c, 6U, y + 24U, (uint16_t)(6U + visible - 1U), y + 24U);
    canvas_set_color(c, ColorBlack);
    return true;
}

bool ui_kit_guide_card_title(
    Canvas* c, uint8_t y, UiKitIcon icon,
    const char* title, const char* short_title) {
    if(!c || icon >= UiKitIconCount || !ui_kit_rect(6U, y + 1U, 10U, 10U) ||
       y > 52U) return false;
    canvas_set_font(c, FontPrimary);
    const char* fitted = ui_kit_guide_fitted(c, title, short_title, 101U);
    if(!fitted) return false;
    ui_kit_icon(c, icon, 6U, y + 1U, 10U, false, false, 0U);
    canvas_set_color(c, ColorBlack);
    canvas_set_font(c, FontPrimary);
    canvas_draw_str(c, 22U, y + 11U, fitted);
    canvas_set_color(c, ColorBlack);
    return true;
}

bool ui_kit_guide_card_description(
    Canvas* c, uint8_t first_baseline,
    const char* first_line, const char* second_line) {
    if(!c || !first_line || first_baseline < 7U || first_baseline > 63U ||
       (second_line && first_baseline > 55U)) return false;
    canvas_set_font(c, FontSecondary);
    if(!ui_kit_guide_fitted(c, first_line, NULL, 116U) ||
       (second_line && !ui_kit_guide_fitted(c, second_line, NULL, 116U)))
        return false;
    canvas_set_color(c, ColorBlack);
    canvas_draw_str(c, 6U, first_baseline, first_line);
    if(second_line) canvas_draw_str(c, 6U, first_baseline + 8U, second_line);
    canvas_set_color(c, ColorBlack);
    return true;
}

bool ui_kit_guide_pin_chip(Canvas* c, uint8_t x, uint8_t y, const char* text) {
    if(!c || !text || !text[0]) return false;
    canvas_set_font(c, FontSecondary);
    const uint16_t text_w = canvas_string_width(c, text);
    if(text_w > 116U) return false;
    const uint16_t chip_w = text_w + 8U;
    if(chip_w < 16U || chip_w > 128U ||
       !ui_kit_rect(x, y, (uint8_t)chip_w, 11U)) return false;
    canvas_set_color(c, ColorBlack);
    canvas_draw_rframe(c, x, y, chip_w, 11U, 3U);
    canvas_draw_str(c, x + 4U, y + 8U, text);
    canvas_set_color(c, ColorBlack);
    return true;
}

void ui_kit_guide_progress(Canvas* c, uint8_t index, uint8_t count) {
    if(!c || !count || index >= count) return;
    canvas_set_color(c, ColorBlack);
    canvas_draw_line(c, 5, 12, 122, 12);
    const uint16_t position = count == 1U ?
        0U : (uint32_t)index * 115U / (count - 1U);
    canvas_draw_box(c, 5U + position, 11U, 3U, 3U);
    canvas_set_color(c, ColorBlack);
}

void ui_kit_guide_scroll_thumb(
    Canvas* c, uint8_t top, uint8_t height,
    uint16_t content_height, uint16_t scroll) {
    if(!c || height < 4U || !ui_kit_rect(127U, top, 1U, height) ||
       content_height <= height) return;
    const uint16_t max_scroll = content_height - height;
    const uint16_t bounded_scroll = scroll > max_scroll ? max_scroll : scroll;
    uint16_t thumb_h = (uint32_t)height * height / content_height;
    if(thumb_h < 4U) thumb_h = 4U;
    if(thumb_h > height) thumb_h = height;
    const uint16_t offset = (uint32_t)bounded_scroll *
        (height - thumb_h) / max_scroll;
    canvas_set_color(c, ColorBlack);
    canvas_draw_line(c, 127U, top + offset, 127U, top + offset + thumb_h - 1U);
    canvas_set_color(c, ColorBlack);
}

/* Instrument Step 1 — additive, render-only components. In particular, none
 * of these helpers reads Furi tick or mutates a capture/session/CSV record. */
static const char* ui_kit_instrument_state_name(UiKitInstrumentState state) {
    switch(state) {
    case UiKitInstrumentReady: return "Ready";
    case UiKitInstrumentLive: return "Live";
    case UiKitInstrumentHeld: return "Held";
    case UiKitInstrumentStopped: return "Stopped";
    case UiKitInstrumentBusy: return "Busy";
    case UiKitInstrumentError: return "Error";
    case UiKitInstrumentWaiting: return "Waiting";
    case UiKitInstrumentMatch: return "Match";
    case UiKitInstrumentOff: return "Off";
    default: return NULL;
    }
}

uint8_t ui_kit_state_chip_width(Canvas* c, UiKitInstrumentState state) {
    if(!c) return 0U;
    const char* name = ui_kit_instrument_state_name(state);
    if(!name) return 0U;
    canvas_set_font(c, FontSecondary);
    const uint16_t width = canvas_string_width(c, name) + 17U;
    return width <= 120U ? (uint8_t)width : 0U;
}

/* All four normal states have visually distinct, non-font procedural marks.
 * The r=2/r=3 discs have circular scan-line silhouettes, NEVER square glyphs.
 * The 11px chip allows a 7px disc at center y=5 without clipping. */
static void ui_kit_instrument_disc(Canvas* c, uint8_t cx, uint8_t cy, uint8_t radius) {
    if(radius == 3U) {
        static const uint8_t half[7] = {1U,2U,3U,3U,3U,2U,1U};
        for(uint8_t i = 0U; i < 7U; ++i)
            canvas_draw_line(c, cx-half[i], cy+i-3U, cx+half[i], cy+i-3U);
    } else {
        static const uint8_t half[5] = {0U,1U,2U,1U,0U};
        for(uint8_t i = 0U; i < 5U; ++i)
            canvas_draw_line(c, cx-half[i], cy+i-2U, cx+half[i], cy+i-2U);
    }
}

static void ui_kit_instrument_glyph(
    Canvas* c, uint8_t x, uint8_t y, UiKitInstrumentState state, bool pulse) {
    const uint8_t gx = x + 7U;
    const uint8_t gy = y + 5U;
    switch(state) {
    case UiKitInstrumentReady:
        canvas_draw_line(c, gx-1U, gy-2U, gx+1U, gy-2U);
        canvas_draw_dot(c, gx-2U, gy-1U);
        canvas_draw_dot(c, gx+2U, gy-1U);
        canvas_draw_dot(c, gx-2U, gy);
        canvas_draw_dot(c, gx+2U, gy);
        canvas_draw_dot(c, gx-2U, gy+1U);
        canvas_draw_dot(c, gx+2U, gy+1U);
        canvas_draw_line(c, gx-1U, gy+2U, gx+1U, gy+2U);
        break;
    case UiKitInstrumentLive:
        ui_kit_instrument_disc(c, gx, gy, pulse ? 3U : 2U);
        break;
    case UiKitInstrumentHeld:
        canvas_draw_box(c, gx-2U, gy-2U, 2U, 5U);
        canvas_draw_box(c, gx+1U, gy-2U, 2U, 5U);
        break;
    case UiKitInstrumentStopped:
        canvas_draw_box(c, gx-2U, gy-2U, 5U, 5U);
        break;
    case UiKitInstrumentBusy:
        canvas_draw_line(c, gx-1U, gy-2U, gx+1U, gy-2U);
        canvas_draw_line(c, gx+1U, gy-2U, gx-1U, gy+2U);
        canvas_draw_line(c, gx-1U, gy+2U, gx+1U, gy+2U);
        break;
    case UiKitInstrumentError:
        /* Preserve the approved Error glyph on existing screens. */
        canvas_draw_line(c, gx, gy-2U, gx, gy);
        canvas_draw_dot(c, gx, gy+2U);
        break;
    case UiKitInstrumentOff:
        canvas_draw_line(c, gx, gy-3U, gx, gy);
        canvas_draw_dot(c, gx, gy+2U);
        break;
    case UiKitInstrumentWaiting:
        /* The Ready/Waiting unfilled disc shares the source glyph. */
        canvas_draw_line(c, gx-1U, gy-2U, gx+1U, gy-2U);
        canvas_draw_dot(c, gx-2U, gy-1U);
        canvas_draw_dot(c, gx+2U, gy-1U);
        canvas_draw_dot(c, gx-2U, gy);
        canvas_draw_dot(c, gx+2U, gy);
        canvas_draw_dot(c, gx-2U, gy+1U);
        canvas_draw_dot(c, gx+2U, gy+1U);
        canvas_draw_line(c, gx-1U, gy+2U, gx+1U, gy+2U);
        break;
    case UiKitInstrumentMatch:
        canvas_draw_line(c, gx-2U, gy, gx-1U, gy+1U);
        canvas_draw_line(c, gx-1U, gy+1U, gx+2U, gy-2U);
        break;
    default: break;
    }
}

static bool ui_kit_state_chip_draw(
    Canvas* c, uint8_t x, uint8_t y,
    UiKitInstrumentState state, bool pulse) {
    if(!c) return false;
    const uint8_t width = ui_kit_state_chip_width(c, state);
    if(!width || !ui_kit_rect(x, y, width, 11U)) return false;
    canvas_set_color(c, ColorBlack);
    canvas_draw_rframe(c, x, y, width, 11U, 3U);
    ui_kit_instrument_glyph(c, x, y, state, pulse);
    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, x + 12U, y + 9U, ui_kit_instrument_state_name(state));
    canvas_set_color(c, ColorBlack);
    return true;
}

bool ui_kit_state_chip_at(
    Canvas* c, uint8_t x, uint8_t y,
    UiKitInstrumentState state, uint32_t tick_ms) {
    return ui_kit_state_chip_draw(c,x,y,state,(tick_ms/500U)%2U != 0U);
}

bool ui_kit_state_chip_compact(
    Canvas* c, UiKitInstrumentState state, bool pulse) {
    const uint8_t width = ui_kit_state_chip_width(c,state);
    if(!width) return false;
    return ui_kit_state_chip_draw(c,(uint8_t)(127U-width),0U,state,pulse);
}

bool ui_kit_instrument_frame(
    Canvas* c, const char* title, const char* short_title,
    const char* context, const char* short_context,
    UiKitInstrumentState state, uint32_t tick_ms) {
    if(!c || !title || !title[0]) return false;
    const uint8_t chip_width = ui_kit_state_chip_width(c, state);
    if(!chip_width) return false;
    const uint8_t chip_x = 124U - chip_width;
    const uint16_t top_room = chip_x > 15U ? chip_x - 15U : 0U;
    canvas_set_font(c, FontSecondary);

    /* Preserve full title, even if that requires chip row two. Only an
     * explicitly supplied short title may be used when full won't fit. */
    const char* chosen_title = title;
    uint16_t tw = canvas_string_width(c, title);
    if(tw > 111U) {
        chosen_title = short_title;
        if(!chosen_title || !chosen_title[0]) return false;
        tw = canvas_string_width(c, chosen_title);
        if(tw > 111U) return false;
    }
    const bool chip_below = tw > top_room;
    const uint16_t context_room = chip_below ?
        (chip_x > 7U ? chip_x - 7U : 0U) : 120U;
    const char* chosen_context = NULL;
    if(context && context[0]) {
        chosen_context = context;
        if(canvas_string_width(c, chosen_context) > context_room)
            chosen_context = short_context;
        if(!chosen_context ||
           canvas_string_width(c, chosen_context) > context_room) return false;
    }
    /* The entire layout has passed its font-width preflight. */
    ui_kit_back_title(c, chosen_title, NULL, NULL);
    if(!ui_kit_state_chip(c, chip_x, chip_below ? 11U : 0U, state, tick_ms))
        return false; /* Width/bounds were preflighted; defensive only. */
    if(chosen_context) {
        canvas_set_font(c, FontSecondary);
        canvas_set_color(c, ColorBlack);
        canvas_draw_str(c, 4U, 19U, chosen_context);
    }
    canvas_set_color(c, ColorBlack);
    return true;
}

static bool ui_kit_instrument_numeric(const char* s) {
    bool has_digit = false;
    for(; *s; ++s) {
        if(*s >= '0' && *s <= '9') has_digit = true;
        else if(*s != '.' && *s != ',' && *s != '-' && *s != '+' &&
                *s != ' ' && *s != '%') return false;
    }
    return has_digit;
}

bool ui_kit_hero_value(
    Canvas* c, const char* label, const char* value,
    const char* unit, uint8_t cx, uint8_t y) {
    if(!c || !label || !label[0] || y < 21U || y > 23U ||
       cx < 16U || cx > 124U) return false;
    canvas_set_font(c, FontSecondary);
    const uint16_t label_width = canvas_string_width(c, label);
    if(!label_width || label_width > (uint16_t)cx - 4U) return false;
    const uint8_t label_x = (uint8_t)(4U + ((uint16_t)cx - 4U - label_width) / 2U);
    const bool has_value = value && value[0];
    const bool has_unit = has_value && unit && unit[0];
    const uint16_t unit_width = has_unit ? canvas_string_width(c, unit) : 0U;
    if(has_unit && (uint16_t)cx + 3U + unit_width > 124U) return false;

    Font value_font = FontSecondary;
    uint16_t value_width = 0U;
    if(has_value) {
        value_font = ui_kit_instrument_numeric(value) ? FontBigNumbers : FontPrimary;
        canvas_set_font(c, value_font);
        value_width = canvas_string_width(c, value);
        if(value_width > (uint16_t)cx - 4U && value_font == FontBigNumbers) {
            value_font = FontPrimary;
            canvas_set_font(c, value_font);
            value_width = canvas_string_width(c, value);
        }
        if(value_width > (uint16_t)cx - 4U) {
            value_font = FontSecondary;
            canvas_set_font(c, value_font);
            value_width = canvas_string_width(c, value);
        }
        if(!value_width || value_width > (uint16_t)cx - 4U) return false;
    }

    /* Draw in two fixed baselines. Fixed right edge prevents layout jitter
     * when digits increase/decrease; the unit never moves with the digits. */
    canvas_set_color(c, ColorBlack);
    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, label_x, y + 6U, label);
    if(has_value) {
        canvas_set_font(c, value_font);
        canvas_draw_str(c, cx - value_width, y + 28U, value);
        if(has_unit) {
            canvas_set_font(c, FontSecondary);
            canvas_draw_str(c, cx + 3U, y + 28U, unit);
        }
    } else {
        canvas_draw_line(c, cx-9U, y + 23U, cx-2U, y + 23U);
    }
    canvas_set_color(c, ColorBlack);
    return true;
}

#undef ui_kit_stat_row
bool ui_kit_stat_row(
    Canvas* c, uint8_t y, const char* label, const char* value) {
    if(!c || !label || !value || !label[0] || !value[0] ||
       !ui_kit_rect(4U, y, 120U, 8U)) return false;
    canvas_set_font(c, FontSecondary);
    const uint16_t left_width = canvas_string_width(c, label);
    const uint16_t right_width = canvas_string_width(c, value);
    if(!left_width || !right_width || left_width + right_width + 4U > 120U)
        return false;
    canvas_set_color(c, ColorBlack);
    canvas_draw_str(c, 4U, y + 7U, label);
    canvas_draw_str(c, 124U - right_width, y + 7U, value);
    canvas_set_color(c, ColorBlack);
    return true;
}


/* ---------- Button + Scope pixel shared primitives (Step 1 only) ---------- */

bool ui_kit_pixel_header(
    Canvas* c, const char* title, bool show_chip,
    UiKitInstrumentState state, bool pulse) {
    if(!c || !title || !title[0]) return false;
    canvas_set_font(c, FontPrimary);
    const uint16_t title_w = canvas_string_width(c, title);
    if(!title_w || 9U + title_w > 127U) return false;
    if(show_chip) {
        const uint8_t chip_w = ui_kit_state_chip_width(c, state);
        if(!chip_w) return false;
        const uint16_t chip_x = 127U - chip_w;
        if(9U + title_w + 2U > chip_x) return false;
    }
    canvas_set_color(c, ColorBlack);
    canvas_draw_line(c, 5U, 2U, 2U, 5U);
    canvas_draw_line(c, 2U, 5U, 5U, 8U);
    canvas_set_font(c, FontPrimary);
    canvas_draw_str(c, 9U, 9U, title);
    if(show_chip && !ui_kit_state_chip_compact(c, state, pulse)) return false;
    canvas_set_color(c, ColorBlack);
    return true;
}

bool ui_kit_stat_row_unit(
    Canvas* c, uint8_t y, const char* label, const char* value,
    const char* unit) {
    if(!c || !label || !label[0] || !value || !value[0] ||
       y < 9U || y > 63U || (unit && unit[0] && unit[0] != ' '))
        return false;
    canvas_set_font(c, FontSecondary);
    const uint16_t label_w = canvas_string_width(c, label);
    const uint16_t unit_w = unit ? canvas_string_width(c, unit) : 0U;
    canvas_set_font(c, FontPrimary);
    const uint16_t value_w = canvas_string_width(c, value);
    if(!label_w || !value_w || label_w > 116U || unit_w > 116U ||
       value_w > 116U || value_w + unit_w > 120U) return false;
    const int32_t unit_x = 124 - (int32_t)unit_w;
    const int32_t value_x = unit_x - (int32_t)value_w;
    if(value_x < 4 + (int32_t)label_w + 4) return false;
    canvas_set_color(c, ColorBlack);
    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, 4U, y, label);
    canvas_set_font(c, FontPrimary);
    canvas_draw_str(c, value_x, y, value);
    if(unit_w) {
        canvas_set_font(c, FontSecondary);
        canvas_draw_str(c, unit_x, y, unit);
    }
    canvas_set_color(c, ColorBlack);
    return true;
}

bool ui_kit_pulse_line_dotted(Canvas* c, uint8_t x, uint8_t y, uint8_t w) {
    if(!c || w < 24U || w > 127U || y < 4U ||
       !ui_kit_rect(x, y-4U, (uint8_t)(w+1U), 5U)) return false;
    const uint16_t knee = (uint16_t)w * 55U / 100U;
    if(knee + 14U > w) return false;
    canvas_set_color(c, ColorBlack);
    for(uint16_t p = 0U; p <= w; p += 2U) {
        int16_t yy = y;
        if(p >= knee && p < knee + 4U) yy = (int16_t)y - (int16_t)(p-knee);
        else if(p >= knee + 4U && p <= knee + 10U) yy = (int16_t)y - 4;
        else if(p > knee + 10U && p < knee + 14U)
            yy = (int16_t)y - 4 + (int16_t)(p-knee-10U);
        canvas_draw_dot(c, (int16_t)x + p, yy);
    }
    canvas_set_color(c, ColorBlack);
    return true;
}

bool ui_kit_mini_trace(
    Canvas* c, uint8_t x, uint8_t y, uint8_t w, uint8_t h,
    const uint8_t* samples, uint16_t count) {
    if(!c || !samples || !count || count > 256U ||
       w < 2U || h < 2U || !ui_kit_rect(x, y, w, h)) return false;
    /* Scan ALL values before drawing. 2/unknown is not a digital sample. */
    for(uint16_t i = 0U; i < count; ++i)
        if(samples[i] > 1U) return false;
    canvas_set_color(c, ColorBlack);
    bool previous_valid = false;
    uint8_t previous = 0U;
    for(uint16_t col = 0U; col < w; ++col) {
        uint16_t first = (uint16_t)((uint32_t)col * count / w);
        uint16_t stop = (uint16_t)((uint32_t)(col + 1U) * count / w);
        if(stop <= first) stop = first + 1U;
        if(stop > count) stop = count;
        uint8_t min_level = samples[first], max_level = samples[first];
        for(uint16_t j = first + 1U; j < stop; ++j) {
            if(samples[j] < min_level) min_level = samples[j];
            if(samples[j] > max_level) max_level = samples[j];
        }
        const uint8_t first_level = samples[first];
        const uint8_t last_level = samples[stop-1U];
        const int16_t px = (int16_t)x + col;
        const int16_t high_y = y, low_y = (int16_t)y + h-1U;
        if(previous_valid && previous != first_level)
            canvas_draw_line(c, px, high_y, px, low_y);
        if(min_level != max_level)
            canvas_draw_line(c, px, high_y, px, low_y);
        else canvas_draw_dot(c, px, first_level ? high_y : low_y);
        previous = last_level;
        previous_valid = true;
    }
    canvas_set_color(c, ColorBlack);
    return true;
}

bool ui_kit_scope_page_dots(Canvas* c, uint8_t active_index) {
    if(!c || active_index >= 4U) return false;
    canvas_set_color(c, ColorBlack);
    for(uint8_t i = 0U; i < 4U; ++i) {
        const uint8_t cx = 100U + 7U * i;
        if(i == active_index) ui_kit_instrument_disc(c, cx, 16U, 2U);
        else canvas_draw_box(c, cx-1U, 15U, 2U, 2U);
    }
    canvas_set_color(c, ColorBlack);
    return true;
}

void ui_kit_next_cue(Canvas* c) {
    if(!c) return;
    canvas_set_color(c, ColorBlack);
    canvas_draw_line(c, 61U, 59U, 65U, 59U);
    canvas_draw_line(c, 62U, 60U, 64U, 60U);
    canvas_draw_dot(c, 63U, 61U);
}
