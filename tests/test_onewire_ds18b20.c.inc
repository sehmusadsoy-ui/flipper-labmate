/* Pure DS18B20 codec tests. No GPIO, no sensor and no thermal measurement. */
#include "labmate_onewire_ds18b20.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static const uint8_t known85[LABMATE_ONEWIRE_SCRATCHPAD_SIZE] = {
    0x50U, 0x05U, 0x4BU, 0x46U, 0x7FU, 0xFFU, 0x0CU, 0x10U, 0x1CU
};
static const uint8_t known250625[LABMATE_ONEWIRE_SCRATCHPAD_SIZE] = {
    0x91U, 0x01U, 0x4BU, 0x46U, 0x7FU, 0xFFU, 0x0CU, 0x10U, 0x70U
};
static const uint8_t knownNeg105[LABMATE_ONEWIRE_SCRATCHPAD_SIZE] = {
    0x58U, 0xFFU, 0x4BU, 0x46U, 0x7FU, 0xFFU, 0x0CU, 0x10U, 0xF9U
};

static void test_crc_and_known_values(void) {
    LabMateOneWireTemperature t;
    assert(labmate_onewire_crc8(known85, 8U) == 0x1CU);
    assert(labmate_onewire_crc8(known85, 9U) == 0U);
    assert(labmate_onewire_crc8(known250625, 8U) == 0x70U);
    assert(labmate_onewire_crc8(knownNeg105, 8U) == 0xF9U);

    memset(&t, 0xA5, sizeof(t));
    assert(labmate_onewire_ds18b20_decode(known85, 9U, false, &t) ==
           LabMateOneWireDecodeConversionUnconfirmed);
    assert(t.resolution_bits == 0U && t.celsius_sixteenths == 0);
    assert(!t.power_on_candidate); /* Unconfirmed data NEVER displayed. */

    assert(labmate_onewire_ds18b20_decode(known85, 9U, true, &t) ==
           LabMateOneWireDecodeOk);
    assert(t.power_on_candidate);
    assert(t.celsius_sixteenths == 85 * 16 && t.resolution_bits == 12U);
    assert(labmate_onewire_celsius_tenths(t.celsius_sixteenths) == 850);

    assert(labmate_onewire_ds18b20_decode(known250625, 9U, true, &t) ==
           LabMateOneWireDecodeOk);
    assert(!t.power_on_candidate && t.celsius_sixteenths == 401);
    assert(labmate_onewire_celsius_tenths(t.celsius_sixteenths) == 251);

    assert(labmate_onewire_ds18b20_decode(knownNeg105, 9U, true, &t) ==
           LabMateOneWireDecodeOk);
    assert(t.celsius_sixteenths == -168 && t.resolution_bits == 12U);
    assert(labmate_onewire_celsius_tenths(t.celsius_sixteenths) == -105);
}

static void test_corruption_and_invalid_inputs(void) {
    uint8_t buf[9U];
    LabMateOneWireTemperature t;
    memset(&t, 0xA5, sizeof(t));
    assert(labmate_onewire_ds18b20_decode(NULL, 9U, true, &t) ==
           LabMateOneWireDecodeInvalidInput);
    assert(t.celsius_sixteenths == 0 && t.resolution_bits == 0U);
    assert(labmate_onewire_ds18b20_decode(known85, 8U, true, &t) ==
           LabMateOneWireDecodeInvalidInput);
    assert(labmate_onewire_ds18b20_decode(known85, 10U, true, &t) ==
           LabMateOneWireDecodeInvalidInput);
    assert(labmate_onewire_ds18b20_decode(known85, 9U, true, NULL) ==
           LabMateOneWireDecodeInvalidInput);
    assert(labmate_onewire_crc8(NULL, 8U) == 0U);

    memcpy(buf, known250625, sizeof(buf));
    buf[3] ^= 1U; /* Data change without matching CRC. */
    assert(labmate_onewire_ds18b20_decode(buf, 9U, true, &t) ==
           LabMateOneWireDecodeCrcMismatch);
    assert(t.celsius_sixteenths == 0 && t.resolution_bits == 0U);

    memcpy(buf, known250625, sizeof(buf));
    buf[4] = 0xFFU; /* DS18B20 config bit7 must be 0. */
    buf[8] = labmate_onewire_crc8(buf, 8U);
    assert(labmate_onewire_ds18b20_decode(buf, 9U, true, &t) ==
           LabMateOneWireDecodeInvalidConfiguration);

    memcpy(buf, known250625, sizeof(buf));
    buf[0] = 0xE0U;
    buf[1] = 0x07U; /* +126 C, impossible for DS18B20. */
    buf[8] = labmate_onewire_crc8(buf, 8U);
    assert(labmate_onewire_ds18b20_decode(buf, 9U, true, &t) ==
           LabMateOneWireDecodeOutOfRange);
    assert(t.celsius_sixteenths == 0);
}

static void test_resolution_limits_and_sign(void) {
    const uint16_t raw = 0x0197U; /* 25.4375 C at 12 bits */
    const uint16_t expected[4] = {0x0190U, 0x0194U, 0x0196U, 0x0197U};
    LabMateOneWireTemperature t;
    uint8_t buf[9U];
    for(unsigned mode=0U; mode<4U; ++mode) {
        memcpy(buf, known250625, sizeof(buf));
        buf[0] = (uint8_t)raw;
        buf[1] = (uint8_t)(raw >> 8U);
        buf[4] = (uint8_t)(0x1FU | (mode << 5U));
        buf[8] = labmate_onewire_crc8(buf, 8U);
        assert(labmate_onewire_ds18b20_decode(buf, 9U, true, &t) ==
               LabMateOneWireDecodeOk);
        assert(t.resolution_bits == 9U + mode);
        assert(t.celsius_sixteenths == (int16_t)expected[mode]);
    }
    /* -55 C is in range and sign conversion is independent of C ABI. */
    memcpy(buf, known250625, sizeof(buf));
    buf[0] = 0x90U; buf[1] = 0xFCU;
    buf[8] = labmate_onewire_crc8(buf, 8U);
    assert(labmate_onewire_ds18b20_decode(buf, 9U, true, &t) ==
           LabMateOneWireDecodeOk);
    assert(t.celsius_sixteenths == -880);
    assert(labmate_onewire_celsius_tenths(t.celsius_sixteenths) == -550);

    buf[0] = 0xD0U; buf[1] = 0x07U; /* +125 C */
    buf[8] = labmate_onewire_crc8(buf, 8U);
    assert(labmate_onewire_ds18b20_decode(buf, 9U, true, &t) ==
           LabMateOneWireDecodeOk);
    assert(t.celsius_sixteenths == 2000);
    assert(labmate_onewire_celsius_tenths(t.celsius_sixteenths) == 1250);
}

static void test_signed_rounding(void) {
    assert(labmate_onewire_celsius_tenths(0) == 0);
    assert(labmate_onewire_celsius_tenths(1) == 1); /* 0.0625C -> 0.1C */
    assert(labmate_onewire_celsius_tenths(-1) == -1);
    assert(labmate_onewire_celsius_tenths(8) == 5);
    assert(labmate_onewire_celsius_tenths(-8) == -5);
    assert(labmate_onewire_celsius_tenths(401) == 251);
    assert(labmate_onewire_celsius_tenths(-401) == -251);
}

int main(void) {
    test_crc_and_known_values();
    test_corruption_and_invalid_inputs();
    test_resolution_limits_and_sign();
    test_signed_rounding();
    puts("1-Wire DS18B20 HOST codec: CRC, signed range, resolution masks, conversion gate, rounding PASS");
    return 0;
}
