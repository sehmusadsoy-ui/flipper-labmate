#include "labmate_monitor_gpio.h"
#include "labmate_capture_core.h"
#include "labmate_resource_policy.h"
#include <furi_hal.h>

void labmate_monitor_gpio_release(LabMateApp* app, uint8_t index) {
    /* Never reclaim PA7 while the generator owns TIM1 PWM in background. */
    if(index >= GPIO_COUNT ||
       !labmate_monitor_pin_allowed(index, app->generator_running)) {
        return;
    }
    furi_hal_gpio_init_simple(labmate_gpio_pins[index], GpioModeAnalog);
}

void labmate_monitor_gpio_activate(LabMateApp* app) {
    /* A previous session may have selected PA7 before background PWM RUN.
     * Switch safely to PC1 without changing TIM1/PA7 ownership.
     */
    app->gpio_index =
        labmate_monitor_entry_pin(app->gpio_index, app->generator_running);
    furi_hal_gpio_init_simple(labmate_gpio_pins[app->gpio_index], GpioModeInput);
    app->gpio_state = furi_hal_gpio_read(labmate_gpio_pins[app->gpio_index]);
    app->gpio_previous_state = app->gpio_state;
}

bool labmate_monitor_gpio_read(uint8_t index) {
    if(index >= GPIO_COUNT) return false;
    return furi_hal_gpio_read(labmate_gpio_pins[index]);
}
