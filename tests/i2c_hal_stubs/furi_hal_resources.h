#pragma once
#include <stdbool.h>
#include <stdint.h>
#ifdef LABMATE_TEST_LEASE_API
#define FURI_HAL_RESOURCE_LEASE_API_V1 1
#define FURI_HAL_LEASE_I2C3_EXT ((1U << 13) | (1U << 5) | (1U << 7))
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask);
bool furi_hal_resource_lease_release(uint32_t handle,uint32_t mask);
#endif
