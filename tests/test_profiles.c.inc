/* Pure v1 profile codec tests: host only, no hardware or microSD. */
#include "labmate_profiles.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>

int main(void) {
    LabMateProfileStore source;
    labmate_profile_store_init(&source);
    source.generation = 0x11223344U;
    source.slots[0].present = true;
    source.slots[0].frequency_pin = 4U;
    source.slots[0].pulse_pin = 5U;
    source.slots[0].generator_index = 14U;
    source.slots[0].logger_source = 2U;
    source.slots[2].present = true;
    source.slots[2].frequency_pin = 1U;
    source.slots[2].pulse_pin = 0U;
    source.slots[2].generator_index = 0U;
    source.slots[2].logger_source = 0U;

    uint8_t buf[LABMATE_PROFILE_BYTES] = {0};
    assert(labmate_profiles_encode(&source, buf));
    assert(memcmp(buf, "LBP1", 4U) == 0);
    assert(buf[4] == 1U && buf[5] == 3U);
    assert(buf[8] == 0x44U && buf[9] == 0x33U &&
           buf[10] == 0x22U && buf[11] == 0x11U);
    assert(buf[17] == 0U && buf[18] == 0U && buf[19] == 0U &&
           buf[20] == 0U && buf[21] == 0U);

    LabMateProfileStore dest;
    labmate_profile_store_init(&dest);
    assert(labmate_profiles_decode(&dest, buf, LABMATE_PROFILE_BYTES));
    assert(dest.generation == source.generation);
    assert(dest.slots[0].present && dest.slots[0].pulse_pin == 5U);
    assert(!dest.slots[1].present);
    assert(dest.slots[2].present && dest.slots[2].frequency_pin == 1U);

    assert(!labmate_profiles_decode(&dest, buf, LABMATE_PROFILE_BYTES - 1U));
    assert(!labmate_profiles_decode(&dest, buf, LABMATE_PROFILE_BYTES + 1U));
    assert(!labmate_profiles_decode(NULL, buf, LABMATE_PROFILE_BYTES));
    assert(!labmate_profiles_decode(&dest, NULL, LABMATE_PROFILE_BYTES));
    for(size_t index = 0U; index < LABMATE_PROFILE_BYTES; ++index) {
        uint8_t corrupt[LABMATE_PROFILE_BYTES];
        memcpy(corrupt, buf, sizeof(corrupt));
        corrupt[index] ^= 1U;
        assert(!labmate_profiles_decode(&dest, corrupt, sizeof(corrupt)));
    }
    /* Decoder must not partially mutate the destination on a damaged file. */
    assert(dest.generation == source.generation);
    assert(dest.slots[0].frequency_pin == 4U);

    LabMateProfileStore invalid = source;
    invalid.slots[0].frequency_pin = 7U;
    uint8_t sentinel[LABMATE_PROFILE_BYTES];
    memset(sentinel, 0xA5, sizeof(sentinel));
    assert(!labmate_profiles_encode(&invalid, sentinel));
    for(size_t i = 0U; i < sizeof(sentinel); ++i) assert(sentinel[i] == 0xA5);
    invalid = source;
    invalid.slots[0].pulse_pin = 4U; /* PB3 not a pulse EXTI pin */
    assert(!labmate_profiles_encode(&invalid, sentinel));
    invalid = source;
    invalid.slots[0].generator_index = LABMATE_PROFILE_GENERATOR_PRESETS;
    assert(!labmate_profiles_encode(&invalid, sentinel));
    invalid = source;
    invalid.slots[0].logger_source = 3U;
    assert(!labmate_profiles_encode(&invalid, sentinel));

    assert(labmate_profiles_is_newer(2U, 1U));
    assert(labmate_profiles_is_newer(0U, UINT32_MAX)); /* wrap */
    assert(!labmate_profiles_is_newer(1U, 1U));
    assert(!labmate_profiles_is_newer(1U, 2U));
    assert(!labmate_profiles_is_newer(0x80000000U, 0U));

    /* DELETE is represented as an absent slot in a NEW generation.
     * Zero every slot field, CRC encode/decode, and retain other slots.
     * No separate filesystem remove operation is involved.
     */
    LabMateProfileStore cleared = source;
    memset(&cleared.slots[0], 0, sizeof(cleared.slots[0]));
    cleared.generation++;
    uint8_t cleared_bytes[LABMATE_PROFILE_BYTES];
    assert(labmate_profiles_encode(&cleared, cleared_bytes));
    assert(labmate_profiles_decode(&dest, cleared_bytes, sizeof(cleared_bytes)));
    assert(!dest.slots[0].present);
    assert(dest.slots[1].present == false);
    assert(dest.slots[2].present);
    assert(dest.generation == source.generation + 1U);
    assert(labmate_profiles_is_newer(dest.generation, source.generation));
    assert(cleared_bytes[12] == 0U && cleared_bytes[13] == 0U &&
           cleared_bytes[14] == 0U && cleared_bytes[15] == 0U &&
           cleared_bytes[16] == 0U);

    puts("LabMate profile codec: valid, corrupt and delete cases passed");
    return 0;
}
