#pragma once
#include "labmate_ui_prefs.h"

LabMateUiPrefsIoResult labmate_ui_prefs_sd_load(
    LabMateUiPreferences* prefs, uint8_t* active_copy);
bool labmate_ui_prefs_sd_save(
    const LabMateUiPreferences* prefs, uint8_t active_copy, uint8_t* written_copy);

