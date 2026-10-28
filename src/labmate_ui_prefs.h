#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Stable identifiers reserved for the eight approved translations.
 * Step 1 deliberately exposes English only until fonts and strings ship. */
typedef enum {
    LabMateLangEnglish = 0,
    LabMateLangTurkish,
    LabMateLangRussian,
    LabMateLangChinese,
    LabMateLangJapanese,
    LabMateLangGerman,
    LabMateLangFrench,
    LabMateLangSpanish,
    LabMateLangCount,
} LabMateUiLanguage;

typedef struct {
    uint8_t language;
    bool animations;
    bool startup_animation;
    uint32_t generation;
} LabMateUiPreferences;

#define LABMATE_UI_PREFS_BYTES 16U
#define LABMATE_UI_PREFS_COPY_NONE 255U

typedef enum {
    LabMateUiPrefsIoEmpty = 0,
    LabMateUiPrefsIoOk,
    LabMateUiPrefsIoCorrupt,
    LabMateUiPrefsIoError,
} LabMateUiPrefsIoResult;

void labmate_ui_prefs_defaults(LabMateUiPreferences* prefs);
bool labmate_ui_prefs_encode(const LabMateUiPreferences* prefs, uint8_t* bytes);
bool labmate_ui_prefs_decode(
    LabMateUiPreferences* prefs, const uint8_t* bytes, size_t len);
bool labmate_ui_prefs_is_newer(uint32_t a, uint32_t b);

