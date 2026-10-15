#pragma once
#include <one_wire/one_wire_host.h>
extern const GpioPin gpio_ext_pa4;
#ifndef TEST_NO_LEASE
#define FURI_HAL_RESOURCE_LEASE_API_V1 1
#define FURI_HAL_LEASE_ONEWIRE_PA4 (1U << 11)
#endif
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask);
bool furi_hal_resource_lease_release(uint32_t handle, uint32_t mask);
