#pragma once
/* Pure Pulse Analyzer mathematics; usable without Flipper SDK or GPIO.
 * Preserve the v1.6 period, 0.1% duty rounding and median-of-five.
 */
#include <stdbool.h>
#include <stdint.h>

#define LABMATE_PULSE_MEDIAN_SAMPLES 5U

/* On false, caller outputs remain unchanged. */
bool labmate_pulse_period_and_duty(
    uint32_t high_cycles,
    uint32_t low_cycles,
    uint32_t* period_cycles,
    uint32_t* duty_permille);

/* Call with five initialized values. No interrupts or hardware access. */
uint32_t labmate_pulse_median5(const uint32_t values[LABMATE_PULSE_MEDIAN_SAMPLES]);
