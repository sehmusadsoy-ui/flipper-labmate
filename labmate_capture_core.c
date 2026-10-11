#include "labmate_capture_core.h"
#include "labmate_resource_policy.h"

const GpioPin* const labmate_gpio_pins[GPIO_COUNT] = {
    &gpio_ext_pc0,
    &gpio_ext_pc1,
    &gpio_ext_pc3,
    &gpio_ext_pb2,
    &gpio_ext_pb3,
    &gpio_ext_pa4,
    &gpio_ext_pa6,
    &gpio_ext_pa7,
};

/* Capture starts may only claim a free owner and an allowed physical pin.
 * Invalid or overlapping requests leave GPIO, EXTI and timers untouched.
 * UI/mode switching still calls capture_stop_all() before changing pins.
 */
bool labmate_capture_can_start(LabMateApp* app, LabMateCaptureOwner requested) {
    const bool allowed = !app->counter_active && labmate_capture_can_acquire(
        app->capture_owner,
        requested,
        app->gpio_index,
        app->frequency_irq_active,
        app->frequency_hw_active,
        app->pulse_irq_active);
    /* GPIO callback and bus-enable HAL functions return void.
     * This status means policy rejected the request, NOT a detected HAL fault.
     */
    app->capture_blocked = !allowed;
    return allowed;
}

