#pragma once

#include <gui/gui.h>
#include <stdint.h>

/* Info v2.0: UI-only sections. These values are not persisted to the SD card. */
typedef enum {
    LabMateInfoHome = 0,
    LabMateInfoGuideList,
    LabMateInfoGuideCard,
    LabMateInfoProject,
    LabMateInfoSafety,
} LabMateInfoSection;

#define LABMATE_INFO_ITEM_COUNT 3U

/* All drawing routines are read-only; no files, GPIO, firmware, or device I/O. */
void labmate_info_draw_home(Canvas* canvas, uint8_t selected, uint8_t pulse_phase);
void labmate_info_draw_home_motion(
    Canvas* canvas, uint8_t selected, uint8_t pulse_phase,
    int8_t slide_px, uint8_t fade_strength);
void labmate_info_draw_guide_list(Canvas* canvas, uint8_t selected);
void labmate_info_draw_guide_list_motion(
    Canvas* canvas, uint8_t selected, int8_t slide_px, uint8_t fade_strength);
void labmate_info_draw_guide_card(Canvas* canvas, uint8_t index, uint8_t scroll_steps);
/* Step 4: six non-blocking display frames. Pure integer geometry functions
 * are reused by the host tests and the app-thread motion tick. */
int16_t labmate_info_scroll_pixel(int16_t from, int16_t to, uint8_t frame);
int8_t labmate_info_slide_pixel(uint8_t frame, int8_t direction);
uint8_t labmate_info_fade_strength(uint8_t frame);
void labmate_info_draw_guide_card_motion(
    Canvas* canvas, uint8_t index, int16_t scroll_px,
    int8_t slide_px, uint8_t fade_strength);
void labmate_info_draw_project(Canvas* canvas);
void labmate_info_draw_project_motion(
    Canvas* canvas, int8_t slide_px, uint8_t fade_strength);
void labmate_info_draw_safety(Canvas* canvas, uint8_t detail_page);
void labmate_info_draw_safety_motion(
    Canvas* canvas, uint8_t detail_page, int8_t slide_px, uint8_t fade_strength);

