#pragma once

#include <gui/gui.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* LabMate Ultimate: monochrome, stateless drawing primitives.
 * All geometry is clamped to the 128x64 screen. No dynamic allocation,
 * hidden I/O, HAL calls, sleeping or input side effects. */
#define UI_KIT_WIDTH 128U
#define UI_KIT_HEIGHT 64U
#define UI_KIT_FRAME_MS 33U
#define UI_KIT_TWEEN_FRAMES 6U
#define UI_KIT_LIST_FIRST_Y 14U
#define UI_KIT_LIST_ROW_H 14U

typedef enum {
    UiKitIconGpio,
    UiKitIconFreq,
    UiKitIconPwm,
    UiKitIconUart,
    UiKitIconI2c,
    UiKitIconScope,
    UiKitIconDoctor,
    UiKitIconDash,
    UiKitIconRec,
    UiKitIconInfo,
    UiKitIconSettings,
    /* Root-carousel assets only; tool-list pictograms remain unchanged. */
    UiKitIconCategoryMeasure,
    UiKitIconCategoryOutput,
    UiKitIconCategoryRecords,
    UiKitIconCategoryComm,
    UiKitIconCount,
} UiKitIcon;

/* Cubic ease-out, integer only. Position may be negative during transitions. */
uint16_t ui_kit_ease(uint8_t frame, uint8_t total);
int16_t ui_kit_lerp(int16_t from, int16_t to, uint8_t frame, uint8_t total);

/* Draw entire label or the explicitly supplied shorter name; never clip
 * or truncate individual glyphs. Returns false if neither will fit. */
bool ui_kit_text(
    Canvas* canvas, int16_t x, int16_t baseline, uint8_t width,
    const char* label, const char* short_label);
void ui_kit_center_text(
    Canvas* canvas, uint8_t baseline, const char* label, const char* short_label);

/* Root: FontSecondary title at left, matching V2.0 at upper right. Both are
 * measured to prevent collision; no font effects or custom bitmaps. */
void ui_kit_brand(Canvas* canvas);

/* Procedural enlargement of the existing LabMate FAP pulse-logo shape. */
void ui_kit_splash_logo(Canvas* canvas, uint8_t x, uint8_t y);

/* Root carousel: two slim vertical focus lines flanking the selected icon.
 * Inactive icons have no tile, and no filled background is drawn. */
void ui_kit_carousel_card(
    Canvas* canvas, uint8_t x, uint8_t y, uint8_t w, uint8_t h, bool selected);

/* One-pixel procedural icons for existing tools; Settings is the exception:
 * its approved 10/14/24px XBM images are used without resampling. */
void ui_kit_icon(
    Canvas* canvas, UiKitIcon icon, int16_t x, int16_t y,
    uint8_t size, bool subdued, bool inverse, uint8_t phase);

/* The one LabMate decoration: idle flat line or a short travelling pulse. */
void ui_kit_pulse_line(
    Canvas* canvas, uint8_t x, uint8_t y, uint8_t width,
    uint8_t phase, bool live);
void ui_kit_page_dots(Canvas* canvas, uint8_t current, uint8_t count);
void ui_kit_pill(Canvas* canvas, uint8_t x, uint8_t y, uint8_t width, uint8_t height);
void ui_kit_panel(Canvas* canvas, uint8_t x, uint8_t y, uint8_t width, uint8_t height);
void ui_kit_confirmation(
    Canvas* canvas, const char* question, const char* short_question,
    const char* action);
/* Same confirmation card with selectable Cancel (left) / action (right).
 * The original ui_kit_confirmation keeps its historic right-selected look. */
void ui_kit_confirmation_choice(
    Canvas* canvas, const char* question, const char* short_question,
    const char* action, bool confirm_selected);
void ui_kit_back_title(Canvas* canvas, const char* name, const char* short_name, const char* pin);
void ui_kit_list_row(
    Canvas* canvas, uint8_t y, UiKitIcon icon, const char* title,
    const char* short_title, bool inverse);
void ui_kit_dither(Canvas* canvas, uint8_t x, uint8_t y, uint8_t width, uint8_t height);
void ui_kit_sparkline(
    Canvas* canvas, const uint8_t* samples, uint8_t count,
    uint8_t x, uint8_t y, uint8_t width, uint8_t height);

/* Doctor Step 1 — additive, stateless, reusable components. Existing screens
 * and their input/diagnostic logic are intentionally unchanged. */
typedef enum {
    UiKitSettingsNormal = 0,
    UiKitSettingsSelected,
    UiKitSettingsEditing,
    UiKitSettingsDisabled,
} UiKitSettingsRowState;

/* Fixed 13px row at y, x=2..125. FontSecondary baseline y+9.
 * Returns false without drawing when the complete label/value cannot fit.
 * Callers must provide an approved short value; no silent truncation. */
bool ui_kit_settings_row(
    Canvas* canvas, uint8_t y, const char* label, const char* value,
    UiKitSettingsRowState state);

/* Settings list variants. The existing Doctor settings_row is unmodified.
 * The caller owns the sliding selection pill; this paints measured content
 * in normal or inverse ink. A row is exactly 13 pixels high. */
typedef enum {
    UiKitSettingsOptionValue = 0,
    UiKitSettingsOptionToggle,
    UiKitSettingsOptionLink,
    UiKitSettingsOptionDestructive,
} UiKitSettingsOptionKind;

/* Switch: 18x9, final state 'on', animation frame 0..4. Inverse is for
 * a dark selection pill. All four corners stay within the given rectangle. */
void ui_kit_toggle(
    Canvas* canvas, uint8_t x, uint8_t y, bool on,
    bool inverse, uint8_t frame);
bool ui_kit_settings_option_row(
    Canvas* canvas, uint8_t y, const char* label, const char* value,
    UiKitSettingsOptionKind kind, bool inverse, bool switch_on,
    uint8_t switch_frame);

/* Transient non-blocking overlay. progress 0..255 moves the panel upward,
 * and 'text' is preflighted as a whole. A procedural check mark is used. */
void ui_kit_toast(Canvas* canvas, const char* text, uint8_t progress);

/* Expanded member of the confirmation family: same dither, rounded panel
 * and Cancel/Reset selection, but enough room for explanatory sentences. */
void ui_kit_confirmation_details(
    Canvas* canvas, bool confirm_selected,
    const char* line_one, const char* line_two, const char* line_three);

/* Distinct drawing variants; no new diagnosis or capture behavior is implied.
 * Bounce is reserved for future evidence, not an active Scope verdict.
 * "Healthy" is visual shorthand only, never a device-health guarantee. */
typedef enum {
    UiKitDiagNoData = 0,
    UiKitDiagStuckHigh,
    UiKitDiagStuckLow,
    UiKitDiagMissingPulse,
    UiKitDiagRuntPulses,
    UiKitDiagJitter,
    UiKitDiagBounce,
    UiKitDiagOffFrequencyDuty,
    UiKitDiagHealthy,
    UiKitDiagCount,
} UiKitDiagKind;

/* Fixed 24x10 canvas_draw_line glyph; no bitmap arrays or dynamic memory. */
void ui_kit_diag_glyph(Canvas* canvas, uint8_t x, uint8_t y, UiKitDiagKind kind);

typedef struct {
    UiKitDiagKind glyph;
    const char* verdict;
    const char* short_verdict;
    const char* reason;
    const char* short_reason;
    const char* reason_second;       /* may be NULL */
    const char* short_reason_second; /* may be NULL */
    const char* action;
    const char* short_action;
    bool advisory; /* true ONLY for evidence-backed real diagnosis */
} UiKitResultCard;

/* Draw only the content below an existing header: 24x10 glyph at (52,12),
 * centered FontPrimary verdict at y=36, reasons at y=45/53, action chip
 * at y=55..63. Fits every string BEFORE drawing. No footer or I/O. */
bool ui_kit_result_card(Canvas* canvas, const UiKitResultCard* card);

/* Info Step 1 — reusable primitives only. None of these routines changes
 * the active screen, handles input, reads pins, or accesses storage. */
typedef enum {
    UiKitKeyOk = 0,
    UiKitKeyOkHold,
    UiKitKeyLeftRight,
    UiKitKeyUpDown,
    UiKitKeyUp,
    UiKitKeyBack,
    /* Required for real Down-only controls (UART TX / Scope pages / details). */
    UiKitKeyDown,
    UiKitKeyCount,
} UiKitKey;

/* Backward-compatible general-position hint used by approved Info screens.
 * Its visual/return contract is unchanged (boolean success). */
bool ui_kit_key_hint_at(
    Canvas* canvas, uint8_t x, uint8_t y, UiKitKey key, const char* label);

/* Pixel-target Instrument hint: exactly y=54, height 10, r=3, label y=62.
 * Returns the exclusive right edge of the label; 0 = no drawing/invalid.
 * LR=18, OK=19, UP=16px. The other key shapes remain supported.
 * Existing five-argument users are dispatched to the unchanged legacy
 * renderer, while new four-argument users get this pixel-target renderer. */
uint8_t ui_kit_key_hint_compact(
    Canvas* canvas, uint8_t x, UiKitKey key, const char* label);

#define UI_KIT_HINT_SELECT(_1,_2,_3,_4,_5,NAME,...) NAME
#define ui_kit_key_hint(...) \
    UI_KIT_HINT_SELECT(__VA_ARGS__,ui_kit_key_hint_at,ui_kit_key_hint_compact,ui_kit_hint_unused)(__VA_ARGS__)

/* A 28px identity card, without a filled background or enclosing frame.
 * phase: 0..UI_KIT_TWEEN_FRAMES reveals the Pulse Line, then a flat line.
 * Until final release the card explicitly says v2.0DEV / E11. */
bool ui_kit_info_identity_card(Canvas* canvas, uint8_t y, uint8_t phase);

/* Common guide-card building blocks. All content is preflighted against its
 * actual font; invalid or overflowing inputs leave the canvas untouched. */
bool ui_kit_guide_card_title(
    Canvas* canvas, uint8_t y, UiKitIcon icon,
    const char* title, const char* short_title);
bool ui_kit_guide_card_description(
    Canvas* canvas, uint8_t first_baseline,
    const char* first_line, const char* second_line);
bool ui_kit_guide_pin_chip(
    Canvas* canvas, uint8_t x, uint8_t y, const char* text);
void ui_kit_guide_progress(
    Canvas* canvas, uint8_t current_index, uint8_t count);
void ui_kit_guide_scroll_thumb(
    Canvas* canvas, uint8_t top, uint8_t height,
    uint16_t content_height, uint16_t scroll);

/* Instrument Step 1 — ADDITIVE display-only primitives. No existing screen
 * calls these until the separate screen-integration steps are approved.
 * Busy/Error are explicit safety states, never disguised as Ready/Stopped. */
typedef enum {
    UiKitInstrumentReady = 0,
    UiKitInstrumentLive,
    UiKitInstrumentHeld,
    UiKitInstrumentStopped,
    UiKitInstrumentBusy,
    UiKitInstrumentError,
    UiKitInstrumentStateCount,
} UiKitInstrumentState;

/* Pixel-target chip: y=0, height 11, r=3, left x=127-width,
 * width=canvas_string_width(FontSecondary,state)+17. New 3-arg callers
 * pass a pulse boolean (furi_get_tick()/500 parity computed by caller).
 * Existing 5-arg frame callers retain explicit x/y/tick semantics.
 * Both draw distinct Ready ring, Live disc, Held bars, Stopped filled box.
 * No clock reads, allocation, or input/capture side effects. */
uint8_t ui_kit_state_chip_width(Canvas* canvas, UiKitInstrumentState state);
bool ui_kit_state_chip_at(
    Canvas* canvas, uint8_t x, uint8_t y,
    UiKitInstrumentState state, uint32_t tick_ms);
bool ui_kit_state_chip_compact(
    Canvas* canvas, UiKitInstrumentState state, bool pulse);
#define UI_KIT_CHIP_SELECT(_1,_2,_3,_4,_5,NAME,...) NAME
#define ui_kit_state_chip(...) \
    UI_KIT_CHIP_SELECT(__VA_ARGS__,ui_kit_state_chip_at,ui_kit_chip_invalid_four,ui_kit_state_chip_compact,ui_kit_chip_unused)(__VA_ARGS__)

/* Header and optional context only: no hero/footer/side effects.
 * Full title is preferred; when it cannot fit with the chip on y=0,
 * the chip moves to y=11 and context uses the remaining x=4..chip gap.
 * Caller supplies an explicit context alternative when needed. If neither
 * title nor context can fit WHOLE, return false without drawing pixels.
 * Caller renders hero (y=22..50) and key hints (y=54..63) separately. */
bool ui_kit_instrument_frame(
    Canvas* canvas, const char* title, const char* short_title,
    const char* context, const char* short_context,
    UiKitInstrumentState state, uint32_t tick_ms);

/* 'cx' is the fixed RIGHT-EDGE anchor for the value, not a moving center.
 * The unit starts 3px after that anchor, on the SAME baseline. Values are
 * drawn whole using BigNumbers (numeric), Primary or Secondary as needed.
 * NULL/empty value draws a procedural dash, never a fake zero.
 * y=22 gives label baseline 28 and hero baseline 50; footer begins at 54.
 * When text cannot fit, returns false and leaves pixels untouched. */
bool ui_kit_hero_value(
    Canvas* canvas, const char* label, const char* value,
    const char* unit, uint8_t cx, uint8_t y);

/* Read-only 8px-high row, no selection, frame, divider or pill.
 * Place at y=21,29,37,45 for four lines before the footer.
 * Full text must fit with a >=4px gap or nothing is drawn. */
bool ui_kit_stat_row(
    Canvas* canvas, uint8_t y, const char* label, const char* value);
