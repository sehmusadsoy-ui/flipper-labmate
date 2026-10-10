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

static void check_capture_ownership(void) {
    for(uint8_t pin = 0U; pin <= LABMATE_MONITOR_PIN_COUNT; ++pin) {
        for(int requested = LabMateCaptureNone;
            requested <= LabMateCapturePulse;
            ++requested) {
            const LabMateCaptureOwner type = (LabMateCaptureOwner)requested;
            const bool permitted = labmate_capture_pin_allowed(type, pin);
            const bool expected =
                (type == LabMateCaptureFrequencyLow && pin == 1U) ||
                (type == LabMateCaptureFrequencyHigh && pin == 4U) ||
                (type == LabMateCapturePulse &&
                 (pin == 0U || pin == 1U || pin == 3U || pin == 5U));
            assert(permitted == expected);
            assert(labmate_capture_can_acquire(
                       LabMateCaptureNone, type, pin, false, false, false) == expected);

            /* No preemption, even when the old IRQ/TIM flags are stale. */
            for(int owner = LabMateCaptureFrequencyLow;
                owner <= LabMateCapturePulse;
                ++owner) {
                assert(!labmate_capture_can_acquire(
                    (LabMateCaptureOwner)owner, type, pin, false, false, false));
            }
            for(unsigned flags = 1U; flags < 8U; ++flags) {
                assert(!labmate_capture_can_acquire(
                    LabMateCaptureNone, type, pin,
                    (flags & 1U) != 0U, (flags & 2U) != 0U,
                    (flags & 4U) != 0U));
            }
        }
    }
    assert(!labmate_capture_pin_allowed(LabMateCapturePulse, UINT8_MAX));
}

static void check_capture_snapshots(void) {
    for(uint8_t pin = 0U; pin <= LABMATE_MONITOR_PIN_COUNT; ++pin) {
        for(int k = LabMateCaptureFrequencyLow; k <= LabMateCapturePulse; ++k) {
            const LabMateCaptureOwner owner = (LabMateCaptureOwner)k;
            const bool allowed = labmate_capture_pin_allowed(owner, pin);
            const bool low = owner == LabMateCaptureFrequencyLow;
            const bool high = owner == LabMateCaptureFrequencyHigh;
            const bool pulse = owner == LabMateCapturePulse;
            assert(labmate_capture_matches(
                owner, owner, pin, pin, low, high, pulse) == allowed);
            assert(!labmate_capture_matches(
                LabMateCaptureNone, owner, pin, pin, low, high, pulse));
            assert(!labmate_capture_matches(
                owner, owner, pin, (uint8_t)(pin + 1U), low, high, pulse));
            assert(!labmate_capture_matches(
                owner, owner, pin, pin, false, false, false));
            assert(!labmate_capture_matches(
                owner, owner, pin, pin, true, true, false));
            assert(!labmate_capture_matches(
                owner, owner, pin, pin, true, false, true));
            assert(!labmate_capture_matches(
                owner, owner, pin, pin, false, true, true));
        }
    }
    assert(!labmate_capture_matches(
        LabMateCaptureNone, LabMateCaptureNone, 0U, 0U, false, false, false));
    assert(!labmate_capture_matches(
        LabMateCapturePulse, LabMateCapturePulse, UINT8_MAX, UINT8_MAX,
        false, false, true));
}

/* Step 6: transition/cleanup contract without touching hardware drivers.
 * A tool may acquire only after the previous owner and every active
 * capture flag have been released; PA7 remains reserved during PWM.
 */
static void check_resource_transitions(void) {
    const LabMateCaptureOwner kinds[] = {
        LabMateCaptureFrequencyLow, LabMateCaptureFrequencyHigh,
        LabMateCapturePulse,
    };
    const uint8_t pins[] = {1U, 4U, 3U};
    for(unsigned previous = 0U; previous < 3U; ++previous) {
        for(unsigned next = 0U; next < 3U; ++next) {
            assert(!labmate_capture_can_acquire(
                kinds[previous], kinds[next], pins[next],
                false, false, false));
            /* Clearing only the owner while leaving any peripheral
             * active must not enable the next capture. */
            for(unsigned mask = 1U; mask < 8U; ++mask) {
                assert(!labmate_capture_can_acquire(
                    LabMateCaptureNone, kinds[next], pins[next],
                    (mask & 1U) != 0U,
                    (mask & 2U) != 0U,
                    (mask & 4U) != 0U));
            }
            assert(labmate_capture_can_acquire(
                LabMateCaptureNone, kinds[next], pins[next],
                false, false, false));
        }
    }
    /* System button EXTI3 (PC3/PB3) and EXTI6 (PA6) must stay
     * excluded from Pulse IRQ acquisition. */
    const uint8_t forbidden[] = {2U, 4U, 6U, 7U};
    for(unsigned i = 0U; i < sizeof(forbidden) / sizeof(forbidden[0]); ++i) {
        assert(!labmate_capture_pin_allowed(LabMateCapturePulse, forbidden[i]));
    }
    assert(!labmate_monitor_pin_allowed(7U, true));
    assert(labmate_monitor_entry_pin(7U, true) == LABMATE_MONITOR_PC1_INDEX);
    assert(labmate_monitor_pin_allowed(7U, false));
}

int main(void) {
    check_resource_transitions();
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
    check_capture_ownership();
    check_capture_snapshots();

    puts("LabMate v1.6 PA7 resource policy: all host-native cases passed");
    return 0;
}
