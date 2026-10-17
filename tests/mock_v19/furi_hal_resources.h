#pragma once
#include <stdint.h>
#include "furi_hal.h"
#define FURI_HAL_RESOURCE_LEASE_API_V1 1
#define FURI_HAL_LEASE_IRQ_PC1 UINT32_C(0x2)
extern const GpioPin gpio_ext_pc1;
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask);
bool furi_hal_resource_lease_release(uint32_t handle, uint32_t mask);
