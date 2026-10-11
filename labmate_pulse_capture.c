#include "labmate_pulse_capture.h"
#include "labmate_capture_core.h"
#include "labmate_capture_exti.h"
#include "labmate_resource_policy.h"
#include <furi_hal.h>
#include <furi_hal_resources.h>

/* Pulse Analyzer uses BOTH edges and the CPU cycle counter.
 * ISR only captures timestamps; all arithmetic stays in the app thread.
 * Like other GPIO tools, it is intended for 3.3V digital signals only.
 */
static void pulse_gpio_callback(void* context) {
    LabMateApp* app = context;
    /* Keep IRQ capture tied to the registered pin, not UI navigation. */
    const GpioPin* pin = labmate_gpio_pins[app->capture_pin_index];
    const uint32_t cycle = DWT->CYCCNT;
    const bool level = furi_hal_gpio_read(pin);

    if(level == app->pulse_irq_level) return;

    if(app->pulse_irq_seen) {
        const uint32_t delta = cycle - app->pulse_irq_last_cycle;
        if(delta > 0U) {
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
            }

            if(fast_half_period > 0U && delta <= fast_half_period) {
                if(app->pulse_irq_level) {
                    app->pulse_irq_high_sum += delta;
                    ++app->pulse_irq_high_samples;
                    if(!wide_window && app->pulse_irq_high_samples >= 16U) {
                        app->pulse_irq_high_cycles =
                            (app->pulse_irq_high_sum + 8U) >> 4;
                        app->pulse_irq_high_valid = true;
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
                    app->pulse_irq_high_sum = 0U;
                    app->pulse_irq_low_sum = 0U;
                    app->pulse_irq_high_samples = 0U;
                    app->pulse_irq_low_samples = 0U;
                }
            } else {
                app->pulse_irq_high_sum = 0U;
                app->pulse_irq_low_sum = 0U;
                app->pulse_irq_high_samples = 0U;
                app->pulse_irq_low_samples = 0U;
                if(app->pulse_irq_level) {
                    app->pulse_irq_high_cycles = delta;
                    app->pulse_irq_high_valid = true;
                } else {
                    app->pulse_irq_low_cycles = delta;
                    app->pulse_irq_low_valid = true;
                }
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

void labmate_pulse_capture_stop(LabMateApp* app) {
    if(!app->pulse_irq_active) return;
    const GpioPin* pin = labmate_gpio_pins[app->capture_pin_index];
    furi_hal_gpio_disable_int_callback(pin);
    furi_hal_gpio_remove_int_callback(pin);

    /* Release both EXTI edge triggers as well as the callback. Merely
     * removing an interrupt callback leaves the rising/falling trigger
     * configuration behind on this firmware version.
     */
    labmate_capture_exti_clear((uint32_t)pin->pin, true);
    app->pulse_irq_active = false;
    if(app->capture_owner == LabMateCapturePulse) {
        app->capture_owner = labmate_capture_owner_after_stop(
            app->capture_owner, LabMateCapturePulse);
        app->capture_pin_index = GPIO_COUNT;
    }
}

void labmate_pulse_capture_start(LabMateApp* app) {
    if(app->pulse_irq_active ||
       !labmate_capture_can_start(app, LabMateCapturePulse)) return;
    const GpioPin* pin = labmate_gpio_pins[app->gpio_index];

    app->pulse_irq_seen = false;
    app->pulse_irq_high_valid = false;
    app->pulse_irq_low_valid = false;
    app->pulse_irq_high_cycles = 0;
    app->pulse_irq_low_cycles = 0;
    app->pulse_irq_edges = 0;
    app->pulse_irq_high_sum = 0;
    app->pulse_irq_low_sum = 0;
    app->pulse_irq_high_samples = 0;
    app->pulse_irq_low_samples = 0;
    app->pulse_irq_wide_window = false;

    furi_hal_gpio_init(
        pin, GpioModeInterruptRiseFall, GpioPullNo, GpioSpeedVeryHigh);
    app->pulse_irq_level = furi_hal_gpio_read(pin);
    app->pulse_irq_last_cycle = DWT->CYCCNT;
    app->pulse_irq_tick_cycle = app->pulse_irq_last_cycle;
    app->pulse_irq_last_tick = furi_get_tick();

    /* Publish pin identity before callback activation. */
    app->capture_pin_index = app->gpio_index;
    furi_hal_gpio_add_int_callback(pin, pulse_gpio_callback, app);
    furi_hal_gpio_enable_int_callback(pin);
    app->pulse_irq_active = true;
    app->capture_owner = LabMateCapturePulse;
}

