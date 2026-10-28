#pragma once

#include "ui_kit.h"
#include <stdint.h>

/* 16 instruments + the original About/Guide = 17 help records. Tool IDs
 * match labmate_navigation.h; they do NOT alter the tool or profile IDs. */
#define LABMATE_INFO_GUIDE_COUNT 17U
#define LABMATE_INFO_GUIDE_PIN_ROWS 3U
#define LABMATE_INFO_GUIDE_PINS_PER_ROW 4U
#define LABMATE_INFO_GUIDE_FACTS 2U
#define LABMATE_INFO_GUIDE_CONTROLS 6U

typedef struct {
    UiKitKey key;
    const char* label;
} LabMateInfoGuideControl;

typedef struct {
    const char* title;
    const char* short_title; /* Explicit FontPrimary fallback only. */
    UiKitIcon icon;
    const char* summary[2]; /* Each line <=21 characters. */
    const char* chips[LABMATE_INFO_GUIDE_PIN_ROWS][LABMATE_INFO_GUIDE_PINS_PER_ROW];
    uint8_t chip_rows;
    const char* facts[LABMATE_INFO_GUIDE_FACTS];
    uint8_t fact_count;
    LabMateInfoGuideControl controls[LABMATE_INFO_GUIDE_CONTROLS];
    uint8_t control_count;
} LabMateInfoGuide;

const LabMateInfoGuide* labmate_info_guide(uint8_t index);
uint8_t labmate_info_guide_max_scroll_steps(uint8_t index);

