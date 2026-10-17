#pragma once
#include "labmate_i2c_session.h"
#include <stdbool.h>
#include <stdint.h>

/* Read-only external I2C3 adapter for PC0 SCL / PC1 SDA.
 * Stock furi_hal_i2c_acquire waits FuriWaitForever and is never used.
 * The optional timed API must be exported by a matching patched Momentum
 * firmware and SDK before enabling this transport at build time.
 */
typedef struct {
    void* stop_context;
    bool (*stop_requested)(void*);
    uint32_t lease_handle; /* shared PC0+PC1+I2C3 claim during HAL ownership */
    bool release_fault; /* sticky: failed firmware release is never ignored */
} LabMateI2cMomentum;

bool labmate_i2c_momentum_available(void);
LabMateI2cSessionOps labmate_i2c_momentum_ops(LabMateI2cMomentum* transport);
