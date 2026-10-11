#pragma once

#include <stdbool.h>
#include <stdint.h>

/* Shared EXTI trigger cleanup. Caller must stop/disable the registered
 * GPIO callback before calling, except when clearing stale triggers
 * before the LOW/PC1 callback is first armed.
 */
void labmate_capture_exti_clear(uint32_t line, bool clear_rising);
