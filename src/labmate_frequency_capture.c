#include "labmate_frequency_capture.h"
#include "labmate_capture_core.h"
#include "labmate_capture_exti.h"
#include "labmate_frequency_tim2.h"
#include "labmate_resource_policy.h"
#include <furi_hal.h>
#include <stm32wbxx_ll_exti.h>

/* Preserve the LOW/PC1 ISR math, HIGH/PB3 ownership and stop ordering of
 * the verified v1.6.1 hardware behavior. No frequency estimation here.
 */
static void frequency_gpio_callback(void* context) {
    LabMateApp* app = context;

    /*
     * High-resolution timestamp.
     * Unsigned subtraction also handles a single
     * 32-bit CYCCNT wrap correctly.
     */
    uint32_t now_cycle = DWT->CYCCNT;

    if(app->frequency_irq_last_cycle != 0) {
        uint32_t period_cycles =
            now_cycle -
            app->frequency_irq_last_cycle;

        /*
         * Above roughly 1 kHz, average 32 complete
         * periods inside the ISR before publishing.
         * This reduces interrupt timing jitter.
         */
        if(SystemCoreClock > 0 &&
           period_cycles <
               (SystemCoreClock / 1000U)) {

            app->frequency_irq_cycle_accumulator +=
                period_cycles;

            app->frequency_irq_accumulated_periods++;

            if(app->frequency_irq_accumulated_periods >= 32U) {
                app->frequency_irq_period_cycles =
                    (app->frequency_irq_cycle_accumulator +
                     16U) /
                    32U;

                app->frequency_irq_new_period = true;

                app->frequency_irq_cycle_accumulator = 0;
                app->frequency_irq_accumulated_periods = 0;
            }
        } else {
            app->frequency_irq_cycle_accumulator = 0;
            app->frequency_irq_accumulated_periods = 0;

            app->frequency_irq_period_cycles =
                period_cycles;

            app->frequency_irq_new_period = true;
        }
    }

    app->frequency_irq_last_cycle = now_cycle;
    app->frequency_irq_last_tick = furi_get_tick();
    app->frequency_irq_edges++;
}

void labmate_frequency_high_stop(LabMateApp* app) {
    if(!app->frequency_hw_active) {
        return;
    }

    labmate_frequency_tim2_shutdown();

    app->frequency_hw_active = false;
    app->frequency_hw_gate_started = false;
    if(app->capture_owner == LabMateCaptureFrequencyHigh) {
        app->capture_owner = labmate_capture_owner_after_stop(
            app->capture_owner, LabMateCaptureFrequencyHigh);
        app->capture_pin_index = GPIO_COUNT;
    }
    app->frequency_hw_last_count = 0;
    app->frequency_hw_last_cycle = 0;
    app->frequency_hw_last_poll_count = 0;
    app->frequency_hw_last_poll_cycle = 0;
}

void labmate_frequency_high_start(LabMateApp* app) {
    if(app->frequency_hw_active ||
       !labmate_capture_can_start(app, LabMateCaptureFrequencyHigh)) {
        return;
    }

    /* Configure PB3/TIM2 with the counter stopped until ownership is published. */
    if(!labmate_frequency_tim2_configure()) {
        app->capture_blocked = true;
        return;
    }

    app->frequency_hw_last_count = 0;
    app->frequency_hw_last_poll_count = 0;
    app->frequency_hw_last_cycle = DWT->CYCCNT;
    app->frequency_hw_last_poll_cycle = app->frequency_hw_last_cycle;
    app->frequency_hw_active = true;
    app->frequency_hw_gate_started = false;
    app->capture_pin_index = app->gpio_index;
    app->capture_owner = LabMateCaptureFrequencyHigh;

    labmate_frequency_tim2_enable();
}
void labmate_frequency_low_stop(LabMateApp* app) {
    if(!app->frequency_irq_active) return;

    /* Detach exactly the pin on which this callback was registered. */
    const GpioPin* pin =
        labmate_gpio_pins[app->capture_pin_index];

    furi_hal_gpio_disable_int_callback(pin);
    furi_hal_gpio_remove_int_callback(pin);

    app->frequency_irq_active = false;
    if(app->capture_owner == LabMateCaptureFrequencyLow) {
        app->capture_owner = labmate_capture_owner_after_stop(
            app->capture_owner, LabMateCaptureFrequencyLow);
        app->capture_pin_index = GPIO_COUNT;
    }
}

void labmate_frequency_low_start(LabMateApp* app) {
    if(app->frequency_irq_active ||
       !labmate_capture_can_start(app, LabMateCaptureFrequencyLow)) {
        return;
    }
    const GpioPin* pin =
        labmate_gpio_pins[app->gpio_index];

    app->frequency_irq_last_cycle = 0;
    app->frequency_irq_period_cycles = 0;
    app->frequency_irq_last_tick = 0;
    app->frequency_irq_edges = 0;
    app->frequency_irq_new_period = false;

    /* Explicitly clear the old falling-edge trigger. Momentum's GPIO init
     * enables rising interrupts but does not always clear falling triggers
     * left by Pulse Analyzer's previous rise/fall EXTI configuration.
     * Without this, a 1 kHz square wave may appear as 2 kHz here.
     */
    labmate_capture_exti_clear(LL_EXTI_LINE_1, false);

    furi_hal_gpio_init(
        pin,
        GpioModeInterruptRise,
        GpioPullNo,
        GpioSpeedVeryHigh);

    /* Publish pin identity before enabling interrupts. */
    app->capture_pin_index = app->gpio_index;
    furi_hal_gpio_add_int_callback(
        pin,
        frequency_gpio_callback,
        app);

    furi_hal_gpio_enable_int_callback(pin);

    app->frequency_irq_active = true;
    app->capture_owner = LabMateCaptureFrequencyLow;
}

