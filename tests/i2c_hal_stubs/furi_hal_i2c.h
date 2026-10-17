#pragma once
#include <stdbool.h>
#include <stdint.h>
typedef struct { unsigned marker; } FuriHalI2cBusHandle;
extern const FuriHalI2cBusHandle furi_hal_i2c_handle_external;
bool furi_hal_i2c_is_device_ready(
    const FuriHalI2cBusHandle*, uint8_t address, uint32_t timeout_ms);
void furi_hal_i2c_release(const FuriHalI2cBusHandle*);
bool furi_hal_i2c_external_acquire_timeout(uint32_t timeout_ms);
