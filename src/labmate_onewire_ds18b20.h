#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* HAL-free, single-sensor DS18B20 scratchpad decoder.
 *
 * It DOES NOT initialize the 1-Wire bus, send CONVERT/READ commands,
 * energize a module or claim that conversion elapsed in real time.
 * The caller must independently prove a completed, properly powered
 * measurement conversion and exclusive GPIO ownership.
 */
#define LABMATE_ONEWIRE_SCRATCHPAD_SIZE 9U

typedef enum {
    LabMateOneWireDecodeInvalidInput = 0,
    LabMateOneWireDecodeCrcMismatch,
    LabMateOneWireDecodeInvalidConfiguration,
    LabMateOneWireDecodeOutOfRange,
    LabMateOneWireDecodeConversionUnconfirmed,
    LabMateOneWireDecodeOk,
} LabMateOneWireDecodeStatus;

typedef struct {
    /* Signed temperature in 1/16 degree Celsius, no floating-point. */
    int16_t celsius_sixteenths;
    uint8_t resolution_bits; /* One of 9, 10, 11, 12. */
    /* Raw +85 C could mean either a real 85 C reading or a power-on
       default. Never treat it alone as evidence of a completed conversion. */
    bool power_on_candidate;
} LabMateOneWireTemperature;

/* Dallas/Maxim reflected CRC-8 polynomial 0x8C (normal form 0x31).
 * CRC over 8 payload bytes must equal scratchpad[8].
 */
uint8_t labmate_onewire_crc8(const uint8_t* bytes, size_t length);

/* `conversion_confirmed` must only be true after an independent actual
 * conversion lifecycle check. The decoder never infers this from CRC.
 * On failure *out remains zero so stale values cannot be displayed.
 */
LabMateOneWireDecodeStatus labmate_onewire_ds18b20_decode(
    const uint8_t* scratchpad,
    size_t length,
    bool conversion_confirmed,
    LabMateOneWireTemperature* out);

/* Signed tenths C, rounded to nearest tenth away from zero on ties. */
int16_t labmate_onewire_celsius_tenths(int16_t sixteenths);
