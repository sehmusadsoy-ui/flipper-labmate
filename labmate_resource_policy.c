#include "labmate_resource_policy.h"

bool labmate_monitor_pin_allowed(uint8_t pin_index, bool generator_running) {
    return pin_index < LABMATE_MONITOR_PIN_COUNT &&
           !(generator_running && pin_index == LABMATE_MONITOR_PA7_INDEX);
}

uint8_t labmate_monitor_entry_pin(uint8_t previous, bool generator_running) {
    return labmate_monitor_pin_allowed(previous, generator_running)
               ? previous
               : LABMATE_MONITOR_PC1_INDEX;
}

uint8_t labmate_monitor_next_pin(
    uint8_t current,
    int8_t direction,
    bool generator_running) {
    uint8_t index = labmate_monitor_entry_pin(current, generator_running);

    /* At least seven pins are always available; bounded eight-step search. */
    for(uint8_t attempts = 0; attempts < LABMATE_MONITOR_PIN_COUNT; ++attempts) {
        if(direction > 0) {
            index = (uint8_t)((index + 1U) % LABMATE_MONITOR_PIN_COUNT);
        } else {
            index = (uint8_t)((index + LABMATE_MONITOR_PIN_COUNT - 1U) %
                              LABMATE_MONITOR_PIN_COUNT);
        }
        if(labmate_monitor_pin_allowed(index, generator_running)) return index;
    }

    /* Defensive fallback; never select PA7 while background PWM owns it. */
    return LABMATE_MONITOR_PC1_INDEX;
}

// No GPIO, timer or interrupt calls here; all of these rules are host-testable.
bool labmate_capture_pin_allowed(LabMateCaptureOwner requested, uint8_t pin_index) {
    if(pin_index >= LABMATE_MONITOR_PIN_COUNT) return false;
    switch(requested) {
    case LabMateCaptureFrequencyLow:
        return pin_index == LABMATE_MONITOR_PC1_INDEX;
    case LabMateCaptureFrequencyHigh:
        return pin_index == 4U; /* PB3 -> TIM2_CH2 */
    case LabMateCapturePulse:
        return pin_index == 0U || pin_index == 1U ||
               pin_index == 3U || pin_index == 5U;
    case LabMateCaptureNone:
    default:
        return false;
    }
}

bool labmate_capture_can_acquire(
    LabMateCaptureOwner owner,
    LabMateCaptureOwner requested,
    uint8_t pin_index,
    bool frequency_low_active,
    bool frequency_high_active,
    bool pulse_active) {
    return owner == LabMateCaptureNone &&
           !frequency_low_active && !frequency_high_active && !pulse_active &&
           labmate_capture_pin_allowed(requested, pin_index);
}

// Pure function: checks software owner, pin identity and active flags.
bool labmate_capture_matches(
    LabMateCaptureOwner owner,
    LabMateCaptureOwner expected,
    uint8_t selected_pin,
    uint8_t owned_pin,
    bool frequency_low_active,
    bool frequency_high_active,
    bool pulse_active) {
    if(owner != expected || owned_pin != selected_pin ||
       !labmate_capture_pin_allowed(expected, selected_pin)) return false;
    switch(expected) {
    case LabMateCaptureFrequencyLow:
        return frequency_low_active && !frequency_high_active && !pulse_active;
    case LabMateCaptureFrequencyHigh:
        return frequency_high_active && !frequency_low_active && !pulse_active;
    case LabMateCapturePulse:
        return pulse_active && !frequency_low_active && !frequency_high_active;
    case LabMateCaptureNone:
    default:
        return false;
    }
}
