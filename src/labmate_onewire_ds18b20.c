#include "labmate_onewire_ds18b20.h"
#include <string.h>

uint8_t labmate_onewire_crc8(const uint8_t* bytes, size_t length) {
    if(!bytes) return 0U;
    uint8_t crc = 0U;
    for(size_t i = 0U; i < length; ++i) {
        uint8_t data = bytes[i];
        for(uint8_t bit = 0U; bit < 8U; ++bit) {
            const bool mix = ((crc ^ data) & 1U) != 0U;
            crc >>= 1U;
            if(mix) crc ^= 0x8CU;
            data >>= 1U;
        }
    }
    return crc;
}

LabMateOneWireDecodeStatus labmate_onewire_ds18b20_decode(
    const uint8_t* scratchpad,
    size_t length,
    bool conversion_confirmed,
    LabMateOneWireTemperature* out) {

    if(!out) return LabMateOneWireDecodeInvalidInput;
    memset(out, 0, sizeof(*out));

    if(!scratchpad || length != LABMATE_ONEWIRE_SCRATCHPAD_SIZE)
        return LabMateOneWireDecodeInvalidInput;

    if(labmate_onewire_crc8(scratchpad, LABMATE_ONEWIRE_SCRATCHPAD_SIZE - 1U) !=
       scratchpad[LABMATE_ONEWIRE_SCRATCHPAD_SIZE - 1U])
        return LabMateOneWireDecodeCrcMismatch;

    /* DS18B20 scratchpad configuration: R1/R0 in bits 6..5,
     * reserved bits 7 and 4..0 fixed to 0 and 11111 respectively. */
    const uint8_t config = scratchpad[4];
    if((config & 0x9FU) != 0x1FU) return LabMateOneWireDecodeInvalidConfiguration;

    const uint8_t resolution = (uint8_t)(9U + ((config >> 5U) & 0x03U));
    const uint8_t fractional_undefined = (uint8_t)(12U - resolution);
    const uint16_t raw = ((uint16_t)scratchpad[1] << 8U) | scratchpad[0];
    const uint16_t mask = (uint16_t)~((1U << fractional_undefined) - 1U);
    const uint16_t quantized = raw & mask;
    const int32_t signed_sixteenths = (quantized & 0x8000U) ?
        (int32_t)quantized - 65536 : (int32_t)quantized;
    if(signed_sixteenths < -55 * 16 || signed_sixteenths > 125 * 16)
        return LabMateOneWireDecodeOutOfRange;

    /* Even a perfect CRC can be an unconverted DS18B20 power-on value.
     * Reject display without real conversion evidence from a future owner. */
    if(!conversion_confirmed) return LabMateOneWireDecodeConversionUnconfirmed;

    out->celsius_sixteenths = (int16_t)signed_sixteenths;
    out->resolution_bits = resolution;
    out->power_on_candidate = quantized == 0x0550U;
    return LabMateOneWireDecodeOk;
}

int16_t labmate_onewire_celsius_tenths(int16_t sixteenths) {
    const int32_t signed_val = sixteenths;
    const int32_t magnitude = signed_val < 0 ? -signed_val : signed_val;
    const int32_t rounded = (magnitude * 10 + 8) / 16;
    return (int16_t)(signed_val < 0 ? -rounded : rounded);
}
