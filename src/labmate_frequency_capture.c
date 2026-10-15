#include "labmate_frequency_capture.h"
#include "labmate_capture_core.h"
#include "labmate_capture_exti.h"
#include "labmate_frequency_tim2.h"
#include "labmate_resource_policy.h"
#include <furi_hal.h>
#include <furi_hal_resources.h>
#include <stm32wbxx_ll_exti.h>

/* Preserve the LOW/PC1 ISR math, HIGH/PB3 ownership and stop ordering of
 * the verified v1.6.1 hardware behavior. No frequency estimation here.
 */
/* DEV E11.1d: opt-in EXTI1/PC1 lease, never use legacy assert-add on
 * a firmware without the matching lease + nonasserting callback ABI.
 * Legacy Momentum HAL users remain outside this experimental protection.
 */
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK)
static uint32_t labmate_frequency_pc1_lease;
#endif

static void frequency_gpio_callback(void* context) {
    LabMateApp* app = context;
    /* TRY-ADD can briefly enable the shared EXTI line before start publishes
     * application state. Ignore any pending/legacy edge during that window.
     */
    if(!app->frequency_irq_active ||
       app->capture_owner != LabMateCaptureFrequencyLow) return;


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
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK)
    /* Do not tear down a GPIO or callback without a matching owned lease. */
    if(labmate_frequency_pc1_lease == 0U) {
        app->capture_blocked = true;
        return;
    }
    const GpioPin* pin = labmate_gpio_pins[app->capture_pin_index];
    furi_hal_gpio_disable_int_callback(pin);
    furi_hal_gpio_remove_int_callback(pin);
    labmate_capture_exti_clear(LL_EXTI_LINE_1, true);
    furi_hal_gpio_init_simple(pin, GpioModeAnalog);

    app->frequency_irq_active = false;
    if(app->capture_owner == LabMateCaptureFrequencyLow) {
        app->capture_owner = labmate_capture_owner_after_stop(
            app->capture_owner, LabMateCaptureFrequencyLow);
        app->capture_pin_index = GPIO_COUNT;
    }
    if(furi_hal_resource_lease_release(
           labmate_frequency_pc1_lease, FURI_HAL_LEASE_IRQ_PC1)) {
        labmate_frequency_pc1_lease = 0U;
    } else {
        /* Never reuse a released pin with an unresolved firmware handle. */
        app->capture_blocked = true;
    }
#else
    /* A mismatched stock SDK can never have started this DEV capture. */
    app->capture_blocked = true;
#endif
}

void labmate_frequency_low_start(LabMateApp* app) {
    if(app->frequency_irq_active ||
       !labmate_capture_can_start(app, LabMateCaptureFrequencyLow)) {
        return;
    }
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK)
    if(labmate_frequency_pc1_lease != 0U) {
        app->capture_blocked = true;
        return;
    }
    const GpioPin* pin = labmate_gpio_pins[app->gpio_index];
    const uint32_t lease = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PC1);
    if(lease == 0U) {
        /* Absolutely no GPIO pin/trigger/callback state touched on denial. */
        app->capture_blocked = true;
        return;
    }
    labmate_frequency_pc1_lease = lease;
    /* Register BEFORE configuring GPIO. A foreign EXTI callback may exist
     * even when it does not participate in the experimental lease table.
     * TRY-ADD rejection must leave that owner's GPIO entirely untouched.
     */
    if(!furi_hal_gpio_try_add_int_callback(pin, frequency_gpio_callback, app)) {
        if(furi_hal_resource_lease_release(
               labmate_frequency_pc1_lease, FURI_HAL_LEASE_IRQ_PC1)) {
            labmate_frequency_pc1_lease = 0U;
        }
        /* Failed release retains handle and denies subsequent starts. */
        app->capture_blocked = true;
        return;
    }

    /* TRY-ADD enables the EXTI IT bit: stop delivery while configuring. */
    furi_hal_gpio_disable_int_callback(pin);
    /* Old falling-edge trigger from Pulse must be cleared after owning the
     * callback and lease, never before checking them.
     */
    labmate_capture_exti_clear(LL_EXTI_LINE_1, false);
    furi_hal_gpio_init(
        pin, GpioModeInterruptRise, GpioPullNo, GpioSpeedVeryHigh);

    app->frequency_irq_last_cycle = 0U;
    app->frequency_irq_period_cycles = 0U;
    app->frequency_irq_last_tick = 0U;
    app->frequency_irq_edges = 0U;
    app->frequency_irq_new_period = false;
    app->capture_pin_index = app->gpio_index;
    app->capture_owner = LabMateCaptureFrequencyLow;
    app->frequency_irq_active = true;
    furi_hal_gpio_enable_int_callback(pin);
#else
    app->capture_blocked = true; /* fail closed: no mismatched HAL fallback */
#endif
}
