#define LABMATE_I18N_IMPL
#include "labmate_i18n.h"
#include "labmate_ui_prefs.h"
#include <string.h>

/* App-thread writes the language; the GUI thread reads it and owns the
 * font-tracking state below. No GPIO, IRQ, storage or capture access. */
static uint8_t i18n_language = LabMateLangEnglish;
/* 0 = unknown/other (no marks), 1 = FontSecondary, 2 = FontPrimary. */
static uint8_t i18n_font = 1U;

typedef struct {
    const char* en;
    const char* tr;
} LabMateI18nEntry;

static const LabMateI18nEntry i18n_table[] = {
#include "labmate_i18n_table.h"
};
#define I18N_COUNT (sizeof(i18n_table) / sizeof(i18n_table[0]))

void labmate_i18n_set_language(uint8_t language) {
    i18n_language = language == LabMateLangTurkish ? LabMateLangTurkish : LabMateLangEnglish;
}

uint8_t labmate_i18n_language(void) {
    return i18n_language;
}

const char* labmate_i18n_tr(const char* text) {
    if(!text || i18n_language != LabMateLangTurkish) return text;
    size_t lo = 0U;
    size_t hi = I18N_COUNT;
    while(lo < hi) {
        const size_t mid = lo + (hi - lo) / 2U;
        const int cmp = strcmp(text, i18n_table[mid].en);
        if(cmp == 0) return i18n_table[mid].tr;
        if(cmp < 0) hi = mid;
        else lo = mid + 1U;
    }
    return text;
}

void labmate_i18n_set_font(Canvas* c, int font) {
    i18n_font = font == (int)FontSecondary ? 1U : font == (int)FontPrimary ? 2U : 0U;
    canvas_set_font(c, (Font)font);
}

void labmate_i18n_frame_begin(Canvas* c) {
    (void)c;
    i18n_font = 1U; /* GUI resets every frame to FontSecondary */
}

typedef enum {
    MarkNone = 0,
    MarkUmlaut, /* o u O U with two dots */
    MarkBreve, /* g G */
    MarkCedilla, /* c s C S */
    MarkDot, /* dotted capital I */
    MarkDotless, /* dotless i: drawn as a plain stem */
} I18nMark;

#define I18N_BUF 72U

/* Decode one Turkish UTF-8 letter; returns its ASCII base or 0. */
static char i18n_special(const uint8_t* p, I18nMark* mark) {
    if(p[0] == 0xC3U) {
        switch(p[1]) {
        case 0x87U: *mark = MarkCedilla; return 'C';
        case 0xA7U: *mark = MarkCedilla; return 'c';
        case 0x96U: *mark = MarkUmlaut; return 'O';
        case 0xB6U: *mark = MarkUmlaut; return 'o';
        case 0x9CU: *mark = MarkUmlaut; return 'U';
        case 0xBCU: *mark = MarkUmlaut; return 'u';
        default: return 0;
        }
    }
    if(p[0] == 0xC4U) {
        switch(p[1]) {
        case 0x9EU: *mark = MarkBreve; return 'G';
        case 0x9FU: *mark = MarkBreve; return 'g';
        case 0xB0U: *mark = MarkDot; return 'I';
        case 0xB1U: *mark = MarkDotless; return 'i';
        default: return 0;
        }
    }
    if(p[0] == 0xC5U) {
        switch(p[1]) {
        case 0x9EU: *mark = MarkCedilla; return 'S';
        case 0x9FU: *mark = MarkCedilla; return 's';
        default: return 0;
        }
    }
    return 0;
}

/* Fold to ASCII base letters. Returns false when the text had no specials. */
static bool i18n_fold(const char* text, char* out, uint8_t* marks) {
    bool special = false;
    size_t n = 0U;
    const uint8_t* p = (const uint8_t*)text;
    while(*p && n + 1U < I18N_BUF) {
        I18nMark mark = MarkNone;
        char base = 0;
        if(*p >= 0xC3U && *p <= 0xC5U && p[1]) base = i18n_special(p, &mark);
        if(base) {
            out[n] = base;
            marks[n] = (uint8_t)mark;
            special = true;
            p += 2;
        } else {
            out[n] = (char)*p;
            marks[n] = MarkNone;
            ++p;
        }
        ++n;
    }
    out[n] = '\0';
    return special;
}

static void i18n_mark(Canvas* c, int32_t x, int32_t y, char base, I18nMark mark) {
    if(i18n_font == 0U) return;
    const bool bold = i18n_font == 2U;
    const int32_t x_height = bold ? 6 : 5;
    const int32_t cap_height = bold ? 8 : 7;
    const bool upper = base >= 'A' && base <= 'Z';
    const int32_t top = upper ? cap_height : x_height;
    /* Both fonts advance one blank column after the ink. */
    int32_t w = (int32_t)canvas_glyph_width(c, (uint16_t)base) - 1;
    if(w < 1) return;
    switch(mark) {
    case MarkUmlaut: {
        const int32_t row = y - top - 2;
        if(bold) {
            const int32_t inset = w >= 7 ? 1 : 0;
            canvas_draw_box(c, x + inset, row, 2, 1);
            canvas_draw_box(c, x + w - 2 - inset, row, 2, 1);
        } else {
            const int32_t inset = w >= 5 ? 1 : 0;
            canvas_draw_dot(c, x + inset, row);
            canvas_draw_dot(c, x + w - 1 - inset, row);
        }
        break;
    }
    case MarkBreve:
        canvas_draw_dot(c, x, y - top - 3);
        canvas_draw_dot(c, x + w - 1, y - top - 3);
        if(w > 2) canvas_draw_box(c, x + 1, y - top - 2, (size_t)(w - 2), 1);
        break;
    case MarkCedilla: {
        const int32_t cx = x + w / 2;
        if(bold) {
            canvas_draw_box(c, cx - 1, y, 2, 1);
            canvas_draw_dot(c, cx - 1, y + 1);
        } else {
            canvas_draw_dot(c, cx, y);
            canvas_draw_dot(c, cx - 1, y + 1);
        }
        break;
    }
    case MarkDot:
        canvas_draw_box(c, x, y - cap_height - 2, bold ? 2 : 1, 1);
        break;
    default:
        break;
    }
}

static uint16_t i18n_width_folded(Canvas* c, const char* folded) {
    return (uint16_t)canvas_string_width(c, folded);
}

/* Draw folded text at a baseline. A dotless i is drawn as a stem so that no
 * colour tracking or pixel erasing is ever needed. */
static void i18n_draw_folded(
    Canvas* c, int32_t x, int32_t y, char* folded, const uint8_t* marks) {
    const size_t len = strlen(folded);
    size_t start = 0U;
    int32_t pen = x;
    for(size_t i = 0U; i <= len; ++i) {
        const bool end = i == len;
        const bool dotless = !end && marks[i] == MarkDotless && i18n_font != 0U;
        if(!end && !dotless) continue;
        if(i > start) {
            const char saved = folded[i];
            folded[i] = '\0';
            canvas_draw_str(c, pen, y, folded + start);
            /* Marks for this run, positioned by measured prefix widths. */
            for(size_t k = start; k < i; ++k) {
                if(marks[k] == MarkNone || marks[k] == MarkDotless) continue;
                const char keep = folded[k];
                folded[k] = '\0';
                const int32_t offset = (int32_t)canvas_string_width(c, folded + start);
                folded[k] = keep;
                i18n_mark(c, pen + offset, y, keep, (I18nMark)marks[k]);
            }
            pen += (int32_t)canvas_string_width(c, folded + start);
            folded[i] = saved;
        }
        if(dotless) {
            const bool bold = i18n_font == 2U;
            const int32_t x_height = bold ? 6 : 5;
            canvas_draw_box(c, pen, y - x_height, bold ? 2 : 1, (size_t)x_height);
            pen += (int32_t)canvas_glyph_width(c, (uint16_t)'i');
        }
        start = i + 1U;
    }
}

void labmate_i18n_draw_str(Canvas* c, int32_t x, int32_t y, const char* s) {
    if(!c || !s) return;
    const char* text = labmate_i18n_tr(s);
    char folded[I18N_BUF];
    uint8_t marks[I18N_BUF];
    if(!i18n_fold(text, folded, marks)) {
        canvas_draw_str(c, x, y, text);
        return;
    }
    i18n_draw_folded(c, x, y, folded, marks);
}

uint16_t labmate_i18n_string_width(Canvas* c, const char* s) {
    if(!c || !s) return 0U;
    const char* text = labmate_i18n_tr(s);
    char folded[I18N_BUF];
    uint8_t marks[I18N_BUF];
    if(!i18n_fold(text, folded, marks)) return (uint16_t)canvas_string_width(c, text);
    return i18n_width_folded(c, folded);
}

void labmate_i18n_draw_str_aligned(
    Canvas* c, int32_t x, int32_t y, int h, int v, const char* s) {
    if(!c || !s) return;
    const char* text = labmate_i18n_tr(s);
    char folded[I18N_BUF];
    uint8_t marks[I18N_BUF];
    if(!i18n_fold(text, folded, marks)) {
        canvas_draw_str_aligned(c, x, y, (Align)h, (Align)v, text);
        return;
    }
    const int32_t width = (int32_t)i18n_width_folded(c, folded);
    if(h == (int)AlignRight) x -= width;
    else if(h == (int)AlignCenter) x -= width / 2;
    /* Same baseline rule as the firmware: ascent is the capital height. */
    const int32_t ascent = i18n_font == 2U ? 8 : 7;
    if(v == (int)AlignTop) y += ascent;
    else if(v == (int)AlignCenter) y += ascent / 2;
    i18n_draw_folded(c, x, y, folded, marks);
}
