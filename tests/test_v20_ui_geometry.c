/* UI-01 initial 128x64 host geometry gate.
 * Compile against real pinned navigation.c and real Scope UI chrome header.
 * This test does NOT claim full 17-screen renderer coverage.
 * cc -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
 *   -fsanitize=address,undefined -fno-omit-frame-pointer \
 *   -Itests/host_stubs -Isrc tests/test_v20_ui_geometry.c \
 *   src/labmate_navigation.c -o /tmp/labmate_ui_geometry && \
 *   /tmp/labmate_ui_geometry
 */
#include "labmate_navigation.h"
#include "labmate_scope_ui.h"
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum { LCD_W = 128, LCD_H = 64, MAX_LABELS = 24 };
typedef struct { int32_t x0, y0, x1, y1; } Rect;
struct Canvas {
    Font font;
    Rect label[MAX_LABELS];
    size_t count;
    unsigned lines;
};

static bool rect_inside(Rect r) {
    return r.x0 >= 0 && r.y0 >= 0 &&
           r.x1 < LCD_W && r.y1 < LCD_H &&
           r.x0 <= r.x1 && r.y0 <= r.y1;
}
static bool rect_intersects(Rect a, Rect b) {
    return !(a.x1 < b.x0 || a.x0 > b.x1 ||
             a.y1 < b.y0 || a.y0 > b.y1);
}
static Rect text_rect(Font f, int32_t x, int32_t baseline, const char* s) {
    assert(s && *s);
    for(const unsigned char* p = (const unsigned char*)s; *p; ++p)
        assert(*p >= 32U && *p <= 126U); /* documented ASCII subset */
    const int32_t glyph_w = f == FontPrimary ? 8 : 6;
    const int32_t glyph_h = f == FontPrimary ? 11 : 8;
    const size_t length = strlen(s);
    assert(length < (size_t)INT32_MAX / 8U);
    return (Rect){x, baseline - glyph_h + 1,
                  x + (int32_t)length * glyph_w - 1, baseline};
}
void canvas_set_font(Canvas* c, Font f) {
    assert(c && (f == FontPrimary || f == FontSecondary));
    c->font = f;
}
void canvas_draw_str(Canvas* c, int32_t x, int32_t y, const char* s) {
    assert(c && c->count < MAX_LABELS);
    const Rect r = text_rect(c->font, x, y, s);
    assert(rect_inside(r));
    for(size_t i = 0; i < c->count; ++i)
        assert(!rect_intersects(r, c->label[i]));
    c->label[c->count++] = r;
}
void canvas_draw_line(Canvas* c, int32_t x0, int32_t y0,
                      int32_t x1, int32_t y1) {
    assert(c && x0 >= 0 && x1 >= 0 && y0 >= 0 && y1 >= 0);
    assert(x0 < LCD_W && x1 < LCD_W && y0 < LCD_H && y1 < LCD_H);
    ++c->lines;
}

static void test_scope_chrome(void) {
    const char* const titles[] = {
        "SCOPE", "COMPARE", "A DETAIL", "B DETAIL", "REFERENCE"
    };
    for(size_t i = 0; i < sizeof(titles) / sizeof(titles[0]); ++i) {
        struct Canvas c = {0};
        assert(labmate_scope_ui_header(&c, titles[i], "1/4"));
        assert(labmate_scope_ui_footer(&c, "(OK)Run", "(v)Pg"));
        assert(c.count == 6U && c.lines == 6U); /* pixel chevron = 2 lines */
        /* Every header is above the graph, every footer below status row. */
        for(size_t n = 0U; n < 3U; ++n) assert(c.label[n].y1 <= 12);
        for(size_t n = 3U; n < 6U; ++n) assert(c.label[n].y0 >= 55);
    }
    struct Canvas active = {0};
    assert(labmate_scope_ui_header(&active, "SCOPE", "1/4"));
    assert(labmate_scope_ui_footer(&active, "(OK)Stop", ""));
    assert(active.count == 5U && active.lines == 5U);
    struct Canvas limits = {0};
    assert(labmate_scope_ui_header(&limits, "123456789", "123"));
    assert(labmate_scope_ui_footer(&limits, "1234567", "12345"));
    assert(limits.count == 6U);
    struct Canvas no_center = {0};
    assert(labmate_scope_ui_footer(&no_center, "12345678901", ""));
    assert(no_center.count == 2U);
    struct Canvas bad = {0};
    assert(!labmate_scope_ui_header(&bad, "1234567890", "1/4"));
    assert(!labmate_scope_ui_header(&bad, "SCOPE", "1234"));
    assert(!labmate_scope_ui_footer(&bad, "12345678", "12345"));
    assert(!labmate_scope_ui_footer(&bad, "123456789012", ""));
    assert(!labmate_scope_ui_footer(&bad, "(OK)Run", "123456"));
    assert(!labmate_scope_ui_header(NULL, "SCOPE", "1/4"));
    assert(!labmate_scope_ui_footer(NULL, "(OK)Run", ""));
    assert(bad.count == 0U && bad.lines == 0U);
    /* Scope plot region from production: x=2..125 and y=15..42. */
    assert(rect_inside((Rect){2, 15, 125, 42}));
    assert(!rect_intersects((Rect){2,15,125,42},
                            (Rect){0,55,127,63}));
}

static void test_menu_text_and_navigation(void) {
    const uint8_t sizes[] = {7U, 2U, 4U, 3U, 1U};
    bool seen[LabMateToolCount] = {false};
    assert(LabMateToolCount == 17 && LabMateGroupCount == 5);
    assert(LabMateGroupComm + 1 == LabMateGroupInfo);
    assert(strcmp(labmate_nav_group_title(LabMateGroupInfo), "INFO") == 0);
    assert(labmate_nav_tool_at(LabMateGroupInfo, 0) == LabMateToolAbout);
    for(uint8_t group = 0; group < LabMateGroupCount; ++group) {
        const uint8_t count = labmate_nav_group_size(group);
        assert(count == sizes[group]);
        /* Current root is a carousel; list header is FontSecondary
         * at x=12, baseline 9, and has no old version badge. */
        const Rect group_title = text_rect(
            FontSecondary, 12, 9, labmate_nav_group_title(group));
        assert(rect_inside(group_title) && group_title.x1 < 98);
        for(uint8_t i = 0; i < count; ++i) {
            const uint8_t tool = labmate_nav_tool_at(group, i);
            assert(tool < LabMateToolCount && !seen[tool]);
            seen[tool] = true;
            for(uint8_t selected = 0; selected < count; ++selected) {
                const uint8_t first = labmate_nav_first_visible(selected, count, 3U);
                assert(first <= selected && selected < (uint8_t)(first + 3U));
                if(i < first || i >= (uint8_t)(first + 3U)) continue;
                const uint8_t row = i - first;
                /* Real ui_kit list: at most 3 rows, y=12,26,40.
                 * The selected 124x14 pill stays above the fourth hint.
                 * Tool text is preflighted against a 91px slot at x=22. */
                const int32_t y = 12 + 14 * row;
                const Rect selected_bg = {2, y, 125, y+13};
                const Rect icon = {6, y+2, 15, y+11};
                const Rect text_slot = {22, y+2, 112, y+10};
                assert(rect_inside(selected_bg) && selected_bg.y1 <= 53);
                assert(rect_inside(icon) && rect_inside(text_slot));
                assert(icon.x1 < text_slot.x0 && text_slot.x1 < 118);
            }
        }
        assert(labmate_nav_tool_at(group, count) == LabMateToolInvalid);
    }
    for(uint8_t tool = 0; tool < LabMateToolCount; ++tool)
        assert(seen[tool]);
    for(uint8_t selected = 0; selected < LabMateGroupCount; ++selected) {
        const uint8_t first = labmate_nav_first_visible(
            selected, LabMateGroupCount, 3U);
        assert(first <= selected && selected < (uint8_t)(first + 3U));
    }
    assert(labmate_nav_wrap(0, 6, -1) == 5);
    assert(labmate_nav_wrap(5, 6, 1) == 0);
    assert(labmate_nav_tool_at(LabMateGroupMeasure, 5) == LabMateToolScope);
    /* Carousel has label baselines 46/55 and page dots at 63.
     * Submenu may display a complete fourth hint at baseline 62. */
    assert(rect_inside(text_rect(FontPrimary, 30, 46, "MEASURE")));
    assert(rect_inside(text_rect(FontSecondary, 20, 55, "7 tools")));
    assert(rect_inside(text_rect(FontSecondary, 22, 62, "Scope")));
}

int main(void) {
    test_scope_chrome();
    test_menu_text_and_navigation();
    puts("UI-01 HOST PASS: pinned navigation + scope chrome 128x64 geometry");
    puts("COVERAGE LIMIT: other renderers, SDK build, device remain UNTESTED");
    return 0;
}
