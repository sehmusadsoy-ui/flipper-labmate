#pragma once
/* Flipper 128x64 Doctor geometry only. Pure C, no HAL/SD/device dependency.
 * Secondary glyph height=8, advance<=6 in the project host geometry model.
 * Keep footer rule at y=52; never place body text baseline on that rule.
 */
#include "labmate_ui_layout.h"
enum {
    LABMATE_DOCTOR_TEXT_X = 4,
    LABMATE_DOCTOR_ROW1_Y = 22,
    LABMATE_DOCTOR_ROW2_Y = 31,
    LABMATE_DOCTOR_ROW3_Y = 40,
    LABMATE_DOCTOR_STATUS_Y = 50,
    LABMATE_DOCTOR_GLYPH_HEIGHT = 8,
    LABMATE_DOCTOR_GLYPH_ADVANCE = 6,
};
