#include "labmate_ui_prefs.h"

/* Fixed byte-order and checksum: independent of compiler struct packing. */
static uint32_t prefs_u32(const uint8_t* b) {
    return (uint32_t)b[0] | ((uint32_t)b[1] << 8U) |
           ((uint32_t)b[2] << 16U) | ((uint32_t)b[3] << 24U);
}

static void prefs_put_u32(uint8_t* b, uint32_t value) {
    b[0] = (uint8_t)value;
    b[1] = (uint8_t)(value >> 8U);
    b[2] = (uint8_t)(value >> 16U);
    b[3] = (uint8_t)(value >> 24U);
}

static uint32_t prefs_crc32(const uint8_t* bytes, size_t len) {
    uint32_t crc = 0xFFFFFFFFU;
    for(size_t i = 0; i < len; ++i) {
        crc ^= bytes[i];
        for(uint8_t bit = 0; bit < 8U; ++bit)
            crc = (crc >> 1U) ^ ((crc & 1U) ? 0xEDB88320U : 0U);
    }
    return ~crc;
}

void labmate_ui_prefs_defaults(LabMateUiPreferences* prefs) {
    if(!prefs) return;
    prefs->language = LabMateLangEnglish;
    prefs->animations = true;
    prefs->startup_animation = true;
    prefs->generation = 0U;
}

bool labmate_ui_prefs_encode(const LabMateUiPreferences* prefs, uint8_t* b) {
    if(!prefs || !b || prefs->language != LabMateLangEnglish) return false;
    b[0] = 'L'; b[1] = 'M'; b[2] = 'U'; b[3] = '1';
    b[4] = 1U;
    b[5] = prefs->language;
    b[6] = (prefs->animations ? 1U : 0U) |
           (prefs->startup_animation ? 2U : 0U);
    b[7] = 0U;
    prefs_put_u32(b + 8U, prefs->generation);
    prefs_put_u32(b + 12U, prefs_crc32(b, 12U));
    return true;
}

bool labmate_ui_prefs_decode(LabMateUiPreferences* prefs, const uint8_t* b, size_t len) {
    if(!prefs || !b || len != LABMATE_UI_PREFS_BYTES ||
       b[0] != 'L' || b[1] != 'M' || b[2] != 'U' || b[3] != '1' ||
       b[4] != 1U || b[5] != LabMateLangEnglish ||
       (b[6] & 0xFCU) || b[7] != 0U ||
       prefs_u32(b + 12U) != prefs_crc32(b, 12U)) return false;

    prefs->language = b[5];
    prefs->animations = (b[6] & 1U) != 0U;
    prefs->startup_animation = (b[6] & 2U) != 0U;
    prefs->generation = prefs_u32(b + 8U);
    return true;
}

bool labmate_ui_prefs_is_newer(uint32_t a, uint32_t b) {
    return (int32_t)(a - b) > 0;
}

