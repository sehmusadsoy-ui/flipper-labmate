#pragma once

#include <stdint.h>

/* PB3 -> TIM2_CH2 external-clock rising-edge counter.
 * The caller must already own LabMateCaptureFrequencyHigh. All hardware
 * configuration and reset is performed here, not from the UI or app loop.
 */
void labmate_frequency_tim2_configure(void);
void labmate_frequency_tim2_enable(void);
uint32_t labmate_frequency_tim2_read(void);
void labmate_frequency_tim2_shutdown(void);
