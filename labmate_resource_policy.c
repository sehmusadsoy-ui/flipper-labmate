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
