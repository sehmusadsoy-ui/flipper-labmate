#include "labmate_profiles.h"

#include <string.h>

static uint32_t labmate_crc32(const uint8_t* data, size_t length) {
    uint32_t crc = UINT32_MAX;
    for(size_t i = 0U; i < length; ++i) {
        crc ^= data[i];
        for(uint8_t bit = 0U; bit < 8U; ++bit) {
            const uint32_t mask = 0U - (crc & 1U);
            crc = (crc >> 1U) ^ (0xEDB88320U & mask);
        }
    }
    return ~crc;
}

static void labmate_store_le32(uint8_t* out, uint32_t value) {
    out[0] = (uint8_t)value;
    out[1] = (uint8_t)(value >> 8U);
    out[2] = (uint8_t)(value >> 16U);
    out[3] = (uint8_t)(value >> 24U);
}

static uint32_t labmate_load_le32(const uint8_t* in) {
    return (uint32_t)in[0] | ((uint32_t)in[1] << 8U) |
           ((uint32_t)in[2] << 16U) | ((uint32_t)in[3] << 24U);
}

void labmate_profile_store_init(LabMateProfileStore* profiles) {
    if(profiles != NULL) memset(profiles, 0, sizeof(*profiles));
}

bool labmate_profile_valid(const LabMateProfile* profile) {
    if(profile == NULL) return false;
    if(!profile->present) return true;
    const bool freq_ok = profile->frequency_pin == 1U ||
                         profile->frequency_pin == 4U;
    const bool pulse_ok = profile->pulse_pin == 0U ||
                          profile->pulse_pin == 1U ||
                          profile->pulse_pin == 3U ||
                          profile->pulse_pin == 5U;
    return freq_ok && pulse_ok &&
           profile->generator_index < LABMATE_PROFILE_GENERATOR_PRESETS &&
           profile->logger_source <= 2U;
}

bool labmate_profiles_encode(
    const LabMateProfileStore* profiles,
    uint8_t output[LABMATE_PROFILE_BYTES]) {
    if(profiles == NULL || output == NULL) return false;

    /* Validate ALL populated slots before touching caller's output. */
    for(uint8_t i = 0U; i < LABMATE_PROFILE_SLOT_COUNT; ++i) {
        if(!labmate_profile_valid(&profiles->slots[i])) return false;
    }

    uint8_t buffer[LABMATE_PROFILE_BYTES] = {0};
    buffer[0] = 'L';
    buffer[1] = 'B';
    buffer[2] = 'P';
    buffer[3] = '1';
    buffer[4] = 1U;
    buffer[5] = LABMATE_PROFILE_SLOT_COUNT;
    labmate_store_le32(buffer + 8U, profiles->generation);

    for(uint8_t i = 0U; i < LABMATE_PROFILE_SLOT_COUNT; ++i) {
        const LabMateProfile* profile = &profiles->slots[i];
        if(!profile->present) continue; /* canonical empty slot: five zeros */
        const size_t offset = 12U + 5U * i;
        buffer[offset] = 1U;
        buffer[offset + 1U] = profile->frequency_pin;
        buffer[offset + 2U] = profile->pulse_pin;
        buffer[offset + 3U] = profile->generator_index;
        buffer[offset + 4U] = profile->logger_source;
    }

    labmate_store_le32(buffer + 28U, labmate_crc32(buffer, 28U));
    memcpy(output, buffer, LABMATE_PROFILE_BYTES);
    return true;
}

bool labmate_profiles_decode(
    LabMateProfileStore* profiles,
    const uint8_t* input,
    size_t length) {
    if(profiles == NULL || input == NULL || length != LABMATE_PROFILE_BYTES)
        return false;
    if(input[0] != 'L' || input[1] != 'B' || input[2] != 'P' ||
       input[3] != '1' || input[4] != 1U ||
       input[5] != LABMATE_PROFILE_SLOT_COUNT ||
       input[6] != 0U || input[7] != 0U || input[27] != 0U)
        return false;
    if(labmate_load_le32(input + 28U) != labmate_crc32(input, 28U))
        return false;

    LabMateProfileStore decoded;
    labmate_profile_store_init(&decoded);
    decoded.generation = labmate_load_le32(input + 8U);
    for(uint8_t i = 0U; i < LABMATE_PROFILE_SLOT_COUNT; ++i) {
        const size_t offset = 12U + 5U * i;
        if(input[offset] > 1U) return false;
        LabMateProfile* profile = &decoded.slots[i];
        profile->present = input[offset] == 1U;
        if(!profile->present) {
            if(input[offset + 1U] != 0U || input[offset + 2U] != 0U ||
               input[offset + 3U] != 0U || input[offset + 4U] != 0U)
                return false;
            continue;
        }
        profile->frequency_pin = input[offset + 1U];
        profile->pulse_pin = input[offset + 2U];
        profile->generator_index = input[offset + 3U];
        profile->logger_source = input[offset + 4U];
        if(!labmate_profile_valid(profile)) return false;
    }
    /* Only commit after validating the complete record. */
    *profiles = decoded;
    return true;
}

bool labmate_profiles_is_newer(uint32_t candidate, uint32_t previous) {
    const uint32_t difference = candidate - previous;
    return difference != 0U && difference < 0x80000000U;
}
