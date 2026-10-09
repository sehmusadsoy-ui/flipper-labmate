#pragma once

#include <stdbool.h>
#include <stdint.h>

/* Pure pin selection rules (no GPIO, IRQ, PWM or firmware API calls).
 * The actual hardware acquire/release operations remain in labmate.c.
 */
#define LABMATE_MONITOR_PIN_COUNT 8U
#define LABMATE_MONITOR_PC1_INDEX 1U
#define LABMATE_MONITOR_PA7_INDEX 7U

/* PA7 is owned by TIM1 PWM while the generator is running in background.
 * Do not reconfigure it for GPIO polling. All other GPIO monitor pins remain
 * selectable. This policy is separate from Pulse Analyzer's EXTI allowlist.
 */
bool labmate_monitor_pin_allowed(uint8_t pin_index, bool generator_running);

/* Re-enter GPIO Monitor on PC1 if its previous pin is now reserved. */
uint8_t labmate_monitor_entry_pin(uint8_t previous, bool generator_running);

/* Preserve original left/right wrapping, except skip reserved PA7. */
uint8_t labmate_monitor_next_pin(
    uint8_t current,
    int8_t direction,
    bool generator_running);

// Exclusive capture owner for LOW/PC1 EXTI, HIGH/PB3 TIM2 and Pulse EXTI.
// Generator TIM1/PA7 has an independent lifecycle.
typedef enum {
    LabMateCaptureNone = 0,
    LabMateCaptureFrequencyLow,
    LabMateCaptureFrequencyHigh,
    LabMateCapturePulse,
} LabMateCaptureOwner;

// Reject invalid capture inputs (Pulse only permits PC0/PC1/PB2/PA4).
bool labmate_capture_pin_allowed(LabMateCaptureOwner requested, uint8_t pin_index);

// Acquire only from a fully released state. The existing capture callbacks,
// timer setup and EXTI cleanup remain in the application core.
bool labmate_capture_can_acquire(
    LabMateCaptureOwner owner,
    LabMateCaptureOwner requested,
    uint8_t pin_index,
    bool frequency_low_active,
    bool frequency_high_active,
    bool pulse_active);
