#pragma once

#include <stdint.h>
#include <stdbool.h>

/* PB3 -> TIM2_CH2 external-clock rising-edge counter.
 * The caller must already own LabMateCaptureFrequencyHigh. All hardware
 * configuration and reset is performed here, not from the UI or app loop.
 */
/* False => no peripheral mutation; unsupported firmware fails closed. */
bool labmate_frequency_tim2_configure(void);
void labmate_frequency_tim2_enable(void);
/* Freeze count without releasing PB3 ownership; used for final snapshot. */
void labmate_frequency_tim2_disable(void);
/* False on a foreign/disappeared TIM2 clock; callers must not
 * interpret a guarded zero read as zero edges.
 */
bool labmate_frequency_tim2_capture_valid(void);
uint32_t labmate_frequency_tim2_read(void);
void labmate_frequency_tim2_shutdown(void);
/* After shutdown, true means failed release left a nonreusable TIM2 lease. */
bool labmate_frequency_tim2_lease_pending(void);
