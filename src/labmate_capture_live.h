#pragma once
/* E11 Live/Held presentation only. Never infer LIVE from an attempted start.
 * Actual IRQ/TIM2 ownership and fault state must be verified first. */
#include <stdbool.h>

static inline bool labmate_frequency_ui_live(
    bool high_pin, bool high_active, bool low_active,
    bool correct_owner, bool blocked, bool release_fault) {
    return (high_pin ? high_active && !low_active :
                       low_active && !high_active) &&
           correct_owner && !blocked && !release_fault;
}

static inline bool labmate_pulse_ui_live(
    bool native_irq_active, bool native_pulse_owner,
    bool blocked, bool release_fault) {
    return native_irq_active && native_pulse_owner && !blocked && !release_fault;
}
