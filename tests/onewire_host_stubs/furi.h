#pragma once
#include <stdint.h>
uint32_t furi_get_tick(void);
uint32_t furi_kernel_get_tick_frequency(void);
#define FURI_CRITICAL_ENTER() do {} while(0)
#define FURI_CRITICAL_EXIT() do {} while(0)
