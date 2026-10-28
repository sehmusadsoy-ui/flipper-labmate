#pragma once

#include <gui/gui.h>
#include <stdint.h>
#include "labmate_ui_prefs.h"

typedef enum {
    LabMateSettingsList = 0,
    LabMateSettingsLanguage,
    LabMateSettingsReset,
} LabMateSettingsPage;

typedef struct {
    uint8_t previous_selected;
    uint8_t selection_frame; /* 0..6 */
    bool selection_motion;
    uint8_t toggle_index;
    uint8_t toggle_frame; /* 0..4 */
    bool toggle_motion;
    uint8_t toast_progress; /* 0 hidden, 1..255 sliding/visible */
    bool toast_reset;
} LabMateSettingsVisual;

void labmate_settings_draw_animated(
    Canvas* canvas, const LabMateUiPreferences* prefs,
    uint8_t selected, LabMateSettingsPage page, uint8_t notice, bool busy,
    bool reset_confirm_selected, const LabMateSettingsVisual* visual);

/* Stateless renderer; safe to run under the normal view mutex. */
void labmate_settings_draw_content(
    Canvas* canvas, const LabMateUiPreferences* prefs,
    uint8_t selected, LabMateSettingsPage page, uint8_t notice, bool busy,
    bool reset_confirm_selected);

