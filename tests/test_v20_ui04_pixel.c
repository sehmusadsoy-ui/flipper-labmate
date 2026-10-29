/* E11 UI04 exact-source Profiles, History, Log Detail display regression.
 * Pixel host models the primitives; actual production draw functions are
 * extracted by the shell runner. No device, GPIO, storage or input dispatch.
 */
#include "labmate_pixel_ui.h"
#include <assert.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef enum { AlignRight = 0 } Align;
typedef enum { AlignBottom = 0 } AlignVertical;
typedef struct {
    bool present;
    uint8_t frequency_pin, generator_index;
} LabMateProfile;
#define LABMATE_PROFILE_SLOT_COUNT 3U
#define LOGGER_HISTORY_LIMIT 32U
typedef struct { LabMateProfile slots[LABMATE_PROFILE_SLOT_COUNT]; } LabMateProfiles;
typedef enum {
    LabMateProfileIoOk, LabMateProfileIoEmpty,
    LabMateProfileIoCorrupt, LabMateProfileIoError
} LabMateProfileIoResult;
typedef enum { LabMateCaptureNone = 0, LabMateCaptureBusy = 1 } LabMateCaptureOwner;
static const uint32_t labmate_generator_frequencies[] = {
    1U, 2U, 5U, 10U, 20U, 50U, 100U, 200U, 500U,
    1000U, 2000U, 5000U, 10000U, 20000U, 50000U
};
typedef struct {
    uint8_t profile_action, profile_selected, profile_notice;
    bool generator_running, logger_recording, profile_busy, profile_confirm;
    LabMateCaptureOwner capture_owner;
    LabMateProfileIoResult profile_io;
    LabMateProfiles profiles;
    uint16_t history_ids[LOGGER_HISTORY_LIMIT];
    uint8_t history_count, history_selected, history_delete_notice, history_mode;
    bool history_busy, history_error, history_delete_confirm, history_delete_mode;
    bool history_loading;
    uint32_t history_rows, history_last_ms;
} LabMateApp;
typedef struct { uint8_t x; UiKitKey key; char label[24]; } DrawnKey;
struct Canvas {
    Font font;
    Color ink;
    unsigned faults, paint, count, headers, frames, boxes, confirmations;
    unsigned key_count;
    char labels[48][64];
    char confirm_question[40], confirm_action[20];
    DrawnKey keys[3];
};

void canvas_set_font(Canvas* c, Font f) { c->font = f; }
void canvas_set_color(Canvas* c, Color v) { c->ink = v; }
uint16_t canvas_string_width(Canvas* c, const char* t) {
    assert(c && t);
    unsigned cell = c->font == FontPrimary ? 8U :
                    c->font == FontBigNumbers ? 10U : 6U;
    return (uint16_t)(strlen(t) * cell);
}
void canvas_draw_str(Canvas* c, int32_t x, int32_t y, const char* t) {
    assert(c && t);
    int32_t w = canvas_string_width(c, t);
    int32_t h = c->font == FontPrimary ? 11 : 8;
    if(w < 1 || x < 0 || x + w > 128 || y < h - 1 || y >= 64)
        c->faults++;
    if(c->count < 48U)
        snprintf(c->labels[c->count++], 64, "%s", t);
    else
        c->faults++;
    c->paint++;
}
void canvas_draw_str_aligned(
    Canvas* c, int32_t x, int32_t y, Align h, AlignVertical v, const char* t) {
    assert(h == AlignRight && v == AlignBottom);
    canvas_draw_str(c, x - canvas_string_width(c, t), y, t);
}
void canvas_draw_line(Canvas* c, int32_t x, int32_t y, int32_t xx, int32_t yy) {
    if(x < 0 || xx < 0 || x >= 128 || xx >= 128 ||
       y < 0 || yy < 0 || y >= 64 || yy >= 64) c->faults++;
    c->paint++;
}
void canvas_draw_box(Canvas* c, int32_t x, int32_t y, int32_t w, int32_t h) {
    if(x < 0 || y < 0 || w <= 0 || h <= 0 || x + w > 128 || y + h > 64)
        c->faults++;
    c->boxes++;
    c->paint++;
}
void canvas_draw_rbox(
    Canvas* c, int32_t x, int32_t y, int32_t w, int32_t h, int32_t r) {
    (void)r;
    if(x < 0 || y < 0 || w <= 0 || h <= 0 || x + w > 128 || y + h > 64)
        c->faults++;
    c->paint++;
}
void canvas_draw_rframe(
    Canvas* c, int32_t x, int32_t y, int32_t w, int32_t h, int32_t r) {
    canvas_draw_rbox(c, x, y, w, h, r);
    c->frames++;
}
void ui_kit_back_title(Canvas* c, const char* title, const char* short_title,
                       const char* pin) {
    (void)short_title; (void)pin;
    c->headers++;
    canvas_set_font(c, FontSecondary);
    canvas_draw_line(c, 7, 2, 4, 5);
    canvas_draw_line(c, 4, 5, 7, 8);
    canvas_draw_str(c, 12, 9, title);
}
uint8_t ui_kit_key_hint_compact(Canvas* c, uint8_t x, UiKitKey key, const char* label) {
    if(!label || c->key_count >= 3U) { c->faults++; return 0U; }
    unsigned width = key == UiKitKeyOk ? 19U : key == UiKitKeyLeftRight ? 18U : 16U;
    unsigned end = x + width + 3U + (unsigned)strlen(label) * 6U;
    if(end > 127U) c->faults++;
    DrawnKey* out = &c->keys[c->key_count++];
    out->x = x; out->key = key;
    snprintf(out->label, sizeof(out->label), "%s", label);
    c->paint++;
    return (uint8_t)end;
}
bool ui_kit_text(Canvas* c, int16_t x, int16_t y, uint8_t width,
                 const char* label, const char* short_label) {
    if(!label) return false;
    canvas_set_font(c, FontSecondary);
    const char* chosen = label;
    if(canvas_string_width(c, chosen) > width) chosen = short_label;
    if(!chosen || canvas_string_width(c, chosen) > width) return false;
    canvas_draw_str(c, x, y, chosen);
    return true;
}
void ui_kit_center_text(Canvas* c, uint8_t y, const char* label,
                        const char* short_label) {
    const char* chosen = label;
    if(canvas_string_width(c, chosen) > 126U) chosen = short_label;
    if(!chosen) { c->faults++; return; }
    unsigned width = canvas_string_width(c, chosen);
    if(width > 126U) { c->faults++; return; }
    canvas_draw_str(c, (int32_t)((128U - width) / 2U), y, chosen);
}
void ui_kit_pulse_line(Canvas* c, uint8_t x, uint8_t y, uint8_t w,
                       uint8_t phase, bool live) {
    (void)phase; (void)live;
    if(x + (unsigned)w >= 128U || y >= 64U) c->faults++;
    canvas_draw_line(c, x, y, x + w, y);
}
void ui_kit_confirmation(Canvas* c, const char* question,
                         const char* short_question, const char* action) {
    assert(question && short_question && action);
    c->confirmations++;
    snprintf(c->confirm_question, sizeof(c->confirm_question), "%s", question);
    snprintf(c->confirm_action, sizeof(c->confirm_action), "%s", action);
    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, 6, 31, question);
}
#include "draw_profiles_e11.inc"
#include "draw_history_e11.inc"
#include "draw_history_detail_e11.inc"

static bool has(const Canvas* c, const char* label) {
    for(unsigned i = 0; i < c->count; i++)
        if(!strcmp(c->labels[i], label)) return true;
    return false;
}
static bool key(const Canvas* c, unsigned i, uint8_t x, UiKitKey id, const char* name) {
    return i < c->key_count && c->keys[i].x == x && c->keys[i].key == id &&
           !strcmp(c->keys[i].label, name);
}
static unsigned verify_profiles(void) {
    unsigned cases = 0;
    for(unsigned selected = 0; selected < 3U; selected++)
    for(unsigned action = 0; action < 3U; action++)
    for(unsigned present = 0; present < 2U; present++)
    for(unsigned scenario = 0; scenario < 12U; scenario++) {
        LabMateApp a = {0};
        Canvas c = {0};
        a.profile_selected = (uint8_t)selected;
        a.profile_action = (uint8_t)action;
        a.profile_io = LabMateProfileIoOk;
        a.profiles.slots[selected].present = present != 0U;
        for(unsigned i = 0; i < 3U; i++) {
            a.profiles.slots[i].generator_index = (uint8_t)(14U - i * 7U);
            a.profiles.slots[i].frequency_pin = (i & 1U) ? 4U : 1U;
        }
        if(scenario == 1U) a.profile_busy = true;
        if(scenario == 2U) a.profile_io = LabMateProfileIoCorrupt;
        if(scenario == 3U) a.profile_io = LabMateProfileIoError;
        if(scenario == 4U) a.generator_running = true;
        if(scenario == 5U) a.capture_owner = LabMateCaptureBusy;
        if(scenario == 6U) a.logger_recording = true;
        if(scenario == 7U) a.profile_notice = 6U;
        if(scenario == 8U) a.profile_notice = 7U;
        if(scenario == 9U) a.profile_notice = 2U;
        if(scenario == 10U) a.profile_confirm = true;
        if(scenario == 11U) { a.profile_confirm = true; a.profile_busy = true; }
        const LabMateApp before = a;
        draw_profiles(&c, &a);
        assert(!memcmp(&a, &before, sizeof(a)));
        assert(c.faults == 0U && c.ink == ColorBlack && c.headers == 1U);
        assert(has(&c, "Profiles"));
        if(a.profile_confirm && !a.profile_busy) {
            assert(c.confirmations == 1U && c.key_count == 0U);
            assert(strstr(c.confirm_question, "S") != NULL);
            assert(!strcmp(c.confirm_action, action == 2U ? "Delete" : "Save"));
        } else {
            assert(c.confirmations == 0U && c.boxes == 1U);
            for(unsigned i = 1; i <= 3U; i++) {
                char id[4];
                snprintf(id, sizeof(id), "S%u", i);
                assert(has(&c, id));
            }
            if(a.profile_busy) {
                assert(c.key_count == 0U && has(&c, "SD BUSY - WAIT"));
            } else {
                const char* operation = action == 0U ? "LOAD" :
                                        action == 1U ? "SAVE" : "DELETE";
                const bool blocked = a.generator_running ||
                                     a.capture_owner != LabMateCaptureNone ||
                                     a.logger_recording;
                assert(c.key_count == 2U);
                assert(key(&c, 0U, 4U, UiKitKeyLeftRight, operation));
                assert(key(&c, 1U, 66U, UiKitKeyOk,
                           blocked ? "Block" : "Select"));
            }
        }
        cases++;
    }
    return cases;
}
static unsigned verify_history(void) {
    static const uint8_t counts[] = {0U, 1U, 3U, 32U};
    unsigned cases = 0;
    for(unsigned ci = 0; ci < 4U; ci++)
    for(unsigned scenario = 0; scenario < 11U; scenario++) {
        LabMateApp a = {0};
        Canvas c = {0};
        a.history_count = counts[ci];
        a.history_selected = a.history_count ? (uint8_t)(a.history_count - 1U) : 0U;
        for(unsigned i = 0; i < 32U; i++)
            a.history_ids[i] = (uint16_t)(i == 31U ? 65535U : 50U + i);
        if(scenario == 1U) a.history_busy = true;
        if(scenario == 2U) a.history_error = true;
        if(scenario == 3U) a.history_delete_mode = true;
        if(scenario == 4U) a.history_delete_notice = 1U;
        if(scenario == 5U) a.history_delete_notice = 2U;
        if(scenario == 6U) { a.history_delete_confirm = true; a.history_delete_mode = true; }
        if(scenario == 7U) { a.history_busy = true; a.history_delete_mode = true; }
        if(scenario == 8U && a.history_count) a.history_selected = 0U;
        if(scenario == 9U && a.history_count) a.history_selected = a.history_count / 2U;
        if(scenario == 10U) { a.history_delete_confirm = true; a.history_busy = true; }
        const LabMateApp before = a;
        draw_history(&c, &a);
        assert(!memcmp(&a, &before, sizeof(a)));
        assert(c.faults == 0U && c.ink == ColorBlack && c.headers == 1U);
        assert(has(&c, "History"));
        if(a.history_delete_confirm && a.history_selected < a.history_count) {
            assert(c.confirmations == 1U && c.key_count == 0U);
            assert(!strcmp(c.confirm_action, "Delete"));
        } else if(a.history_busy || a.history_error || !a.history_count) {
            assert(c.confirmations == 0U && c.key_count == 1U);
            assert(key(&c, 0U, 4U, UiKitKeyBack, "Menu"));
            if(!a.history_count && !a.history_busy && !a.history_error)
                assert(has(&c, "No saved logs"));
        } else {
            assert(c.confirmations == 0U && c.key_count == 2U && c.boxes == 1U);
            assert(key(&c, 0U, 4U, UiKitKeyLeftRight, "Mode"));
            assert(key(&c, 1U, 66U, UiKitKeyOk,
                       a.history_delete_mode ? "Delete" : "Open"));
        }
        cases++;
    }
    return cases;
}
static unsigned verify_detail(void) {
    unsigned cases = 0;
    for(unsigned valid = 0; valid < 2U; valid++)
    for(unsigned state = 0; state < 5U; state++)
    for(unsigned mode = 0; mode < 4U; mode++) {
        LabMateApp a = {0};
        Canvas c = {0};
        a.history_count = valid ? 1U : 0U;
        a.history_ids[0] = 65535U;
        a.history_mode = (uint8_t)mode;
        a.history_rows = state & 1U ? UINT32_MAX : 0U;
        a.history_last_ms = state & 1U ? UINT32_MAX : 0U;
        if(state == 1U) a.history_loading = true;
        if(state == 2U) a.history_busy = true;
        if(state == 3U) a.history_error = true;
        if(state == 4U) { a.history_busy = true; a.history_error = true; }
        const LabMateApp before = a;
        draw_history_detail(&c, &a);
        assert(!memcmp(&a, &before, sizeof(a)));
        assert(c.faults == 0U && c.ink == ColorBlack && c.headers == 1U);
        assert(has(&c, "Log view") && has(&c, "READ ONLY"));
        assert(c.key_count == 1U && key(&c, 0U, 4U, UiKitKeyBack, "List"));
        if(!valid) assert(has(&c, "NO LOG SELECTED"));
        else if(a.history_busy) assert(has(&c, "OPENING SD..."));
        else if(a.history_error) assert(has(&c, "SD READ ERROR"));
        else {
            assert(has(&c, "FILE") && has(&c, "MODE") && has(&c, "TIME"));
            assert(has(&c, a.history_loading ? "READ ROWS" : "ROWS"));
            assert(has(&c, "log_65535.csv"));
        }
        cases++;
    }
    return cases;
}
int main(void) {
    const unsigned p = verify_profiles();
    const unsigned h = verify_history();
    const unsigned d = verify_detail();
    assert(p == 216U && h == 44U && d == 40U);
    printf("E11 UI04 PRODUCTION RENDER HOST PASS: profiles=%u history=%u detail=%u total=%u\n",
           p, h, d, p + h + d);
    return 0;
}
