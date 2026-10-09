/* Host-native checks for the v1.6 GPIO Monitor pin ownership policy.
 * Compile as ordinary C: no Flipper Zero headers or hardware are required.
 * These are logic tests, not proof of on-device electrical behavior.
 */
#include "labmate_resource_policy.h"

#include <assert.h>
#include <stdio.h>

static void check_sequence(bool generator_running) {
    for(uint8_t pin = 0U; pin < LABMATE_MONITOR_PIN_COUNT; ++pin) {
        for(int8_t direction = -1; direction <= 1; direction += 2) {
            const uint8_t from =
                labmate_monitor_entry_pin(pin, generator_running);
            uint8_t expected = from;
            do {
                expected = direction > 0
                               ? (uint8_t)((expected + 1U) % LABMATE_MONITOR_PIN_COUNT)
                               : (uint8_t)((expected + LABMATE_MONITOR_PIN_COUNT - 1U) %
                                           LABMATE_MONITOR_PIN_COUNT);
            } while(!labmate_monitor_pin_allowed(expected, generator_running));

            const uint8_t next =
                labmate_monitor_next_pin(pin, direction, generator_running);
            assert(next == expected);
            assert(labmate_monitor_pin_allowed(next, generator_running));
        }
    }
}

int main(void) {
    /* All eight pins remain available when the generator is off. */
    for(uint8_t pin = 0U; pin < LABMATE_MONITOR_PIN_COUNT; ++pin) {
        assert(labmate_monitor_pin_allowed(pin, false));
    }

    assert(!labmate_monitor_pin_allowed(LABMATE_MONITOR_PIN_COUNT, false));
    assert(!labmate_monitor_pin_allowed(UINT8_MAX, false));
    assert(!labmate_monitor_pin_allowed(7U, true));
    assert(labmate_monitor_pin_allowed(6U, true));
    assert(labmate_monitor_pin_allowed(0U, true));

    /* PWM running: skip PA7 on both sides of the wrap. */
    assert(labmate_monitor_next_pin(6U, +1, true) == 0U);
    assert(labmate_monitor_next_pin(0U, -1, true) == 6U);

    /* PWM off: normal wrapping and PA7 are restored. */
    assert(labmate_monitor_next_pin(6U, +1, false) == 7U);
    assert(labmate_monitor_next_pin(0U, -1, false) == 7U);
    assert(labmate_monitor_next_pin(7U, +1, false) == 0U);

    /* Re-entering GPIO Monitor when PA7 was previously selected must not
     * replace the PWM output pin configuration.
     */
    assert(labmate_monitor_entry_pin(7U, true) == LABMATE_MONITOR_PC1_INDEX);
    assert(labmate_monitor_entry_pin(7U, false) == 7U);
    assert(labmate_monitor_entry_pin(UINT8_MAX, true) ==
           LABMATE_MONITOR_PC1_INDEX);
    assert(labmate_monitor_next_pin(7U, +1, true) == 2U);
    assert(labmate_monitor_next_pin(7U, -1, true) == 0U);

    check_sequence(false);
    check_sequence(true);

    puts("LabMate v1.6 PA7 resource policy: all host-native cases passed");
    return 0;
}
