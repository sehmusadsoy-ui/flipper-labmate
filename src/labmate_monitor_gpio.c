#include "labmate_monitor_gpio.h"
#include "labmate_capture_core.h"
#include "labmate_resource_policy.h"
#include <furi_hal.h>

void labmate_monitor_gpio_release(LabMateApp* app, uint8_t index) {
    /* Keep PA7 untouched after a denied or unresolved TIM1 lease, too. */
    const bool pa7_reserved =
        app->generator_running || app->generator_blocked ||
        app->generator_release_fault;
    if(index >= GPIO_COUNT ||
       !labmate_monitor_pin_allowed(index, pa7_reserved)) {
        return;
    }
    furi_hal_gpio_init_simple(labmate_gpio_pins[index], GpioModeAnalog);
}

void labmate_monitor_gpio_activate(LabMateApp* app) {
    /* A previous session may have selected PA7 before background PWM RUN.
     * Switch safely to PC1 without changing TIM1/PA7 ownership.
     */
    const bool pa7_reserved =
        app->generator_running || app->generator_blocked ||
        app->generator_release_fault;
    app->gpio_index =
        labmate_monitor_entry_pin(app->gpio_index, pa7_reserved);
    furi_hal_gpio_init_simple(labmate_gpio_pins[app->gpio_index], GpioModeInput);
    app->gpio_state = furi_hal_gpio_read(labmate_gpio_pins[app->gpio_index]);
    app->gpio_previous_state = app->gpio_state;
}

bool labmate_monitor_gpio_read(uint8_t index) {
    if(index >= GPIO_COUNT) return false;
    return furi_hal_gpio_read(labmate_gpio_pins[index]);
}
