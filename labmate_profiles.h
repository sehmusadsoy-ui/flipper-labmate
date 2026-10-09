#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Canonical, portable v1.6 profile representation.
 * Codec ONLY: no microSD reads/writes, no menu actions, no automatic restore.
 * Future storage layer may use redundant profiles_a/b files.
 *
 * 32-byte on-disk record (little-endian generation):
 *  0..3  "LBP1"          4 version=1   5 slot_count=3
 *  6..7  reserved=0      8..11 generation (LE32)
 * 12..26 three slots of five bytes each:
 *          present, frequency_pin, pulse_pin, generator_index, logger_source
 * 27     reserved=0      28..31 CRC32(0..27) LE32
 */
#define LABMATE_PROFILE_BYTES 32U
#define LABMATE_PROFILE_SLOT_COUNT 3U
#define LABMATE_PROFILE_GENERATOR_PRESETS 15U

typedef struct {
    bool present;
    uint8_t frequency_pin; /* PC1=1 or PB3=4 */
    uint8_t pulse_pin; /* PC0=0, PC1=1, PB2=3, PA4=5 */
    uint8_t generator_index; /* 0..14, never running state */
    uint8_t logger_source; /* FREQ LOW=0, FREQ HIGH=1, PULSE=2 */
} LabMateProfile;

typedef struct {
    uint32_t generation;
    LabMateProfile slots[LABMATE_PROFILE_SLOT_COUNT];
} LabMateProfileStore;

void labmate_profile_store_init(LabMateProfileStore* profiles);
bool labmate_profile_valid(const LabMateProfile* profile);
bool labmate_profiles_encode(
    const LabMateProfileStore* profiles,
    uint8_t output[LABMATE_PROFILE_BYTES]);
bool labmate_profiles_decode(
    LabMateProfileStore* profiles,
    const uint8_t* input,
    size_t length);
/* Serial wrap-safe generation comparison; 2^31 difference is ambiguous. */
bool labmate_profiles_is_newer(uint32_t candidate, uint32_t previous);
