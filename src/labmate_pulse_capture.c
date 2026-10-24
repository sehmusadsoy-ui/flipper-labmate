#include "labmate_pulse_capture.h"
#include "labmate_capture_core.h"
#include "labmate_doctor_pulse_bridge.h"
#include "labmate_capture_exti.h"
#include "labmate_resource_policy.h"
#include <furi_hal.h>
#include <furi_hal_resources.h>

/* Pulse Analyzer uses BOTH edges and the CPU cycle counter.
 * ISR only captures timestamps; all arithmetic stays in the app thread.
 * E11 experimental ownership applies to PC0, PC1, PB2, PA4 individually.
 * A stock SDK must fail closed, not fall back to assert-based callbacks.
 */
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK)
static uint32_t labmate_pulse_lease_handle;
static uint32_t labmate_pulse_lease_mask;

static uint32_t labmate_pulse_mask_for_pin(uint8_t index) {
    switch(index) {
    case 0U: return FURI_HAL_LEASE_IRQ_PC0;
    case 1U: return FURI_HAL_LEASE_IRQ_PC1;
    case 3U: return FURI_HAL_LEASE_IRQ_PB2;
    case 5U: return FURI_HAL_LEASE_IRQ_PA4;
    default: return 0U;
    }
}

static void pulse_gpio_callback(void* context) {
    LabMateApp* app = context;
    /* Try-add briefly enables EXTI before the application publishes owner. */
    if(!app->pulse_irq_active || app->capture_owner != LabMateCapturePulse) return;
    /* Keep IRQ capture tied to the registered pin, not UI navigation. */
    const GpioPin* pin = labmate_gpio_pins[app->capture_pin_index];
    const uint32_t cycle = DWT->CYCCNT;
    const bool level = furi_hal_gpio_read(pin);

    if(level == app->pulse_irq_level) return;

    if(app->pulse_irq_seen) {
        const uint32_t delta = cycle - app->pulse_irq_last_cycle;
        if(delta > 0U) {
            bool new_high=false;
            bool new_low=false;
            /* At ordinary frequencies preserve the 16-sample response.
             * For very short pulses, collect 128 HIGH and 128 LOW widths
             * and publish them TOGETHER. Independent publications could
             * otherwise mix widths from different moments on the LCD.
             * This reduces random timing jitter, not systematic latency.
             */
            const uint32_t fast_half_period = SystemCoreClock / 1000U;
            const uint32_t short_half_period = SystemCoreClock / 25000U;
            const bool wide_window =
                short_half_period > 0U && delta <= short_half_period;

            if(app->pulse_irq_wide_window != wide_window) {
                app->pulse_irq_high_sum = 0U;
                app->pulse_irq_low_sum = 0U;
                app->pulse_irq_high_samples = 0U;
                app->pulse_irq_low_samples = 0U;
                app->pulse_irq_wide_window = wide_window;
                /* Never combine phase estimates from different smoothing modes. */
                labmate_pulse_pair_discard_partial(&app->pulse_pair_audit);
            }

            if(fast_half_period > 0U && delta <= fast_half_period) {
                if(app->pulse_irq_level) {
                    app->pulse_irq_high_sum += delta;
                    ++app->pulse_irq_high_samples;
                    if(!wide_window && app->pulse_irq_high_samples >= 16U) {
                        app->pulse_irq_high_cycles =
                            (app->pulse_irq_high_sum + 8U) >> 4;
                        app->pulse_irq_high_valid = true;
                        new_high=true;
                        app->pulse_irq_high_sum = 0U;
                        app->pulse_irq_high_samples = 0U;
                    }
                } else {
                    app->pulse_irq_low_sum += delta;
                    ++app->pulse_irq_low_samples;
                    if(!wide_window && app->pulse_irq_low_samples >= 16U) {
                        app->pulse_irq_low_cycles =
                            (app->pulse_irq_low_sum + 8U) >> 4;
                        app->pulse_irq_low_valid = true;
                        new_low=true;
                        app->pulse_irq_low_sum = 0U;
                        app->pulse_irq_low_samples = 0U;
                    }
                }

                if(wide_window &&
                   app->pulse_irq_high_samples >= 128U &&
                   app->pulse_irq_low_samples >= 128U) {
                    app->pulse_irq_high_cycles =
                        (app->pulse_irq_high_sum +
                         app->pulse_irq_high_samples / 2U) /
                        app->pulse_irq_high_samples;
                    app->pulse_irq_low_cycles =
                        (app->pulse_irq_low_sum +
                         app->pulse_irq_low_samples / 2U) /
                        app->pulse_irq_low_samples;
                    app->pulse_irq_high_valid = true;
                    app->pulse_irq_low_valid = true;
                    new_high=true;
                    new_low=true;
                    app->pulse_irq_high_sum = 0U;
                    app->pulse_irq_low_sum = 0U;
                    app->pulse_irq_high_samples = 0U;
                    app->pulse_irq_low_samples = 0U;
                }
            } else {
                /* At extreme duty (e.g. 100 Hz / 95%), one phase can be
                 * long (>1 ms) while the other needs 16 short samples.
                 * A long HIGH must not erase the LOW averaging window,
                 * nor a long LOW erase HIGH samples. Only reset the
                 * completed phase's pending fast-width accumulator. */
                if(app->pulse_irq_level) {
                    app->pulse_irq_high_sum = 0U;
                    app->pulse_irq_high_samples = 0U;
                    app->pulse_irq_high_cycles = delta;
                    app->pulse_irq_high_valid = true;
                    new_high=true;
                } else {
                    app->pulse_irq_low_sum = 0U;
                    app->pulse_irq_low_samples = 0U;
                    app->pulse_irq_low_cycles = delta;
                    app->pulse_irq_low_valid = true;
                    new_low=true;
                }
            }
            /* One new paired publication requires one fresh completed update
             * of BOTH phases. These are averaging windows, not necessarily
             * widths from the same individual waveform cycle. */
            /* 20k IRQ/s is possible: skip publication audit work
             * unless this transition truly completed a phase window. */
            if(new_high || new_low) {
                (void)labmate_pulse_pair_note(
                    &app->pulse_pair_audit, new_high, new_low,
                    app->pulse_irq_high_valid, app->pulse_irq_low_valid,
                    app->pulse_irq_high_cycles, app->pulse_irq_low_cycles,
                    app->pulse_irq_edges + 1U);
            }
        }
    }

    app->pulse_irq_level = level;
    app->pulse_irq_seen = true;
    app->pulse_irq_last_cycle = cycle;
    /* Avoid a kernel tick call on every edge (20,000 IRQ/s at 10 kHz).
     * Refresh the stale-signal timestamp at most once every 10 ms.
     * A slow signal still updates it on each edge.
     */
    const uint32_t tick_gap_cycles = SystemCoreClock / 100U;
    if(tick_gap_cycles == 0U ||
       (uint32_t)(cycle - app->pulse_irq_tick_cycle) >= tick_gap_cycles) {
        app->pulse_irq_last_tick = furi_get_tick();
        app->pulse_irq_tick_cycle = cycle;
    }
    app->pulse_irq_edges++;
}

#endif /* matching firmware experimental GPIO/lease ABI */

void labmate_pulse_capture_stop(LabMateApp* app) {
    if(!app->pulse_irq_active) return;
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK)
    if(labmate_pulse_lease_handle == 0U || labmate_pulse_lease_mask == 0U) {
        app->capture_blocked = true;
        return; /* not our pin/callback; never reset foreign peripherals */
    }
    const GpioPin* pin = labmate_gpio_pins[app->capture_pin_index];
    furi_hal_gpio_disable_int_callback(pin);
    furi_hal_gpio_remove_int_callback(pin);
    /* Only an owned EXTI line may have its rising/falling triggers cleared. */
    labmate_capture_exti_clear((uint32_t)pin->pin, true);
    furi_hal_gpio_init_simple(pin, GpioModeAnalog);
    app->pulse_irq_active = false;
    if(furi_hal_resource_lease_release(
           labmate_pulse_lease_handle, labmate_pulse_lease_mask)) {
        labmate_pulse_lease_handle = 0U;
        labmate_pulse_lease_mask = 0U;
        /* Neither HOLD nor callback-detach alone certifies lease release. */
        if(app->capture_owner == LabMateCapturePulse) {
            app->capture_owner = labmate_capture_owner_after_stop(
                app->capture_owner, LabMateCapturePulse);
            app->capture_pin_index = GPIO_COUNT;
        }
    } else {
        /* Lost release: retain the handle and reject any later restart. */
        app->capture_release_fault = true;
        app->capture_blocked = true;
    }
#else
    app->capture_blocked = true;
#endif
}

bool labmate_pulse_lease_pending(void) {
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK)
    return labmate_pulse_lease_handle != 0U || labmate_pulse_lease_mask != 0U;
#else
    return false;
#endif
}

void labmate_pulse_capture_start(LabMateApp* app) {
    if(app->pulse_irq_active ||
       !labmate_capture_can_start(app, LabMateCapturePulse)) return;
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK)
    if(labmate_pulse_lease_handle != 0U || labmate_pulse_lease_mask != 0U) {
        app->capture_blocked = true;
        return;
    }
    const uint32_t mask = labmate_pulse_mask_for_pin(app->gpio_index);
    if(mask == 0U) {
        app->capture_blocked = true;
        return;
    }
    const GpioPin* pin = labmate_gpio_pins[app->gpio_index];
    const uint32_t handle = furi_hal_resource_lease_try_acquire(mask);
    if(handle == 0U) {
        app->capture_blocked = true;
        return; /* no GPIO or EXTI mutations on denied owner */
    }
    labmate_pulse_lease_handle = handle;
    labmate_pulse_lease_mask = mask;
    /* If any uncoordinated service already occupies the EXTI callback
     * slot, do NOT configure or reset its GPIO. */
    if(!furi_hal_gpio_try_add_int_callback(pin, pulse_gpio_callback, app)) {
        if(furi_hal_resource_lease_release(handle, mask)) {
            labmate_pulse_lease_handle = 0U;
            labmate_pulse_lease_mask = 0U;
        } else {
            app->capture_release_fault = true;
        }
        app->capture_blocked = true;
        return;
    }
    furi_hal_gpio_disable_int_callback(pin);
    app->pulse_irq_seen = false;
    app->pulse_irq_high_valid = false;
    app->pulse_irq_low_valid = false;
    app->pulse_irq_high_cycles = 0U;
    app->pulse_irq_low_cycles = 0U;
    app->pulse_irq_edges = 0U;
    app->pulse_irq_high_sum = 0U;
    app->pulse_irq_low_sum = 0U;
    app->pulse_irq_high_samples = 0U;
    app->pulse_irq_low_samples = 0U;
    app->pulse_irq_wide_window = false;
    /* The native callback is disabled after owning its E11 lease. */
    labmate_pulse_pair_reset(&app->pulse_pair_audit);
    app->pulse_pair_last_observation = (LabMatePulsePairObservation){0};

    furi_hal_gpio_init(
        pin, GpioModeInterruptRiseFall, GpioPullNo, GpioSpeedVeryHigh);
    app->pulse_irq_level = furi_hal_gpio_read(pin);
    app->pulse_irq_last_cycle = DWT->CYCCNT;
    app->pulse_irq_tick_cycle = app->pulse_irq_last_cycle;
    app->pulse_irq_last_tick = furi_get_tick();
    app->capture_pin_index = app->gpio_index;
    app->capture_owner = LabMateCapturePulse;
    app->pulse_irq_active = true;
    furi_hal_gpio_enable_int_callback(pin);
    /* Started only AFTER native callback installation and ownership. */
    labmate_doctor_pulse_started(app);
#else
    app->capture_blocked = true;
#endif
}
