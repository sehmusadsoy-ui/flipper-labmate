#define LABMATE_I18N_IMPL
#include "labmate_i18n.h"
#include "labmate_ui_prefs.h"
#include <furi.h>
#include <storage/storage.h>
#include <stdlib.h>
#include <string.h>

/* Language and table change only under the UI mutex (labmate_i18n_swap);
 * the GUI thread reads them under the same mutex and owns the font state.
 * No GPIO, IRQ or capture access. The table lives on SD, never in .rodata. */
static uint8_t i18n_language = LabMateLangEnglish;
/* 0 = unknown/other (no marks), 1 = FontSecondary, 2 = FontPrimary. */
static uint8_t i18n_font = 1U;

/* files/i18n_tr.bin, built by scripts/gen-i18n-tr.py. */
#define I18N_PATH APP_ASSETS_PATH("i18n_tr.bin")
#define I18N_MAX_BYTES 16384U
#define I18N_HEADER 8U
#define I18N_ENTRY 8U

typedef struct {
    uint16_t count;
    const uint8_t* entries; /* count x {u32 hash, u16 offset, u16 0} */
    const char* blob;
    uint32_t blob_size;
    uint8_t data[];
} LabMateI18nTable;

static LabMateI18nTable* i18n_table;

static uint32_t i18n_hash(const char* s) {
    uint32_t h = 0x811C9DC5U;
    while(*s) {
        h ^= (uint8_t)*s++;
        h *= 0x01000193U;
    }
    return h;
}

static uint32_t i18n_u32(const uint8_t* p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static uint16_t i18n_u16(const uint8_t* p) {
    return (uint16_t)(p[0] | (p[1] << 8));
}

/* Accept the table only if every offset lands on a NUL-terminated string. */
static bool i18n_validate(LabMateI18nTable* t, uint32_t size) {
    const uint8_t* d = t->data;
    if(size < I18N_HEADER || memcmp(d, "LMT1", 4) != 0) return false;
    const uint16_t count = i18n_u16(d + 4);
    const uint32_t index_end = I18N_HEADER + (uint32_t)count * I18N_ENTRY;
    if(!count || index_end >= size || d[size - 1U] != 0U) return false;
    t->count = count;
    t->entries = d + I18N_HEADER;
    t->blob = (const char*)(d + index_end);
    t->blob_size = size - index_end;
    uint32_t previous = 0U;
    for(uint16_t i = 0U; i < count; ++i) {
        const uint8_t* e = t->entries + (uint32_t)i * I18N_ENTRY;
        const uint32_t hash = i18n_u32(e);
        if(i && hash <= previous) return false; /* strictly sorted, unique */
        previous = hash;
        if(i18n_u16(e + 4) >= t->blob_size) return false;
    }
    return true;
}

void* labmate_i18n_load_turkish(void) {
    Storage* storage = furi_record_open(RECORD_STORAGE);
    if(!storage) return NULL;
    LabMateI18nTable* table = NULL;
    File* file = storage_file_alloc(storage);
    if(file) {
        if(storage_file_open(file, I18N_PATH, FSAM_READ, FSOM_OPEN_EXISTING)) {
            const uint64_t size = storage_file_size(file);
            if(size > I18N_HEADER && size <= I18N_MAX_BYTES) {
                table = malloc(sizeof(LabMateI18nTable) + (size_t)size);
                if(table &&
                   (storage_file_read(file, table->data, (size_t)size) != (size_t)size ||
                    !i18n_validate(table, (uint32_t)size))) {
                    free(table);
                    table = NULL;
                }
            }
        }
        storage_file_close(file); /* required even after a failed open */
        storage_file_free(file);
    }
    furi_record_close(RECORD_STORAGE);
    return table;
}

void* labmate_i18n_swap(uint8_t language, void* table) {
    void* previous = i18n_table;
    i18n_table = table;
    i18n_language = language == LabMateLangTurkish && table ? LabMateLangTurkish :
                                                               LabMateLangEnglish;
    return previous;
}

void labmate_i18n_free(void* table) {
    free(table);
}

uint8_t labmate_i18n_language(void) {
    return i18n_language;
}

const char* labmate_i18n_tr(const char* text) {
    const LabMateI18nTable* t = i18n_table;
    if(!text || !t || i18n_language != LabMateLangTurkish) return text;
    const uint32_t hash = i18n_hash(text);
    uint32_t lo = 0U;
    uint32_t hi = t->count;
    while(lo < hi) {
        const uint32_t mid = lo + (hi - lo) / 2U;
        const uint8_t* e = t->entries + mid * I18N_ENTRY;
        const uint32_t h = i18n_u32(e);
        if(h == hash) return t->blob + i18n_u16(e + 4);
        if(h < hash) lo = mid + 1U;
        else hi = mid;
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
