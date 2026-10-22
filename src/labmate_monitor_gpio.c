#include "labmate_monitor_gpio.h"
#include "labmate_capture_core.h"
#include "labmate_resource_policy.h"
#include <furi_hal.h>
#include <furi_hal_resources.h>

/* E11 experimental pin-only firmware leases. These overlap our IRQ/TIM/I2C
 * lease bits, but DO NOT intercept independent legacy firmware GPIO writers.
 * Monitor owns one input pin at a time; no EXTI callback is registered.
 * A stock/unmatched SDK fails closed instead of touching a foreign pin.
 */
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_LEASE_MONITOR_PA6)
static uint32_t labmate_monitor_lease_handle;
static uint32_t labmate_monitor_lease_mask;
static uint8_t labmate_monitor_lease_index = GPIO_COUNT;

static uint32_t labmate_monitor_mask(uint8_t index) {
    switch(index) {
    case 0U: return FURI_HAL_LEASE_MONITOR_PC0;
    case 1U: return FURI_HAL_LEASE_MONITOR_PC1;
    case 2U: return FURI_HAL_LEASE_MONITOR_PC3;
    case 3U: return FURI_HAL_LEASE_MONITOR_PB2;
    case 4U: return FURI_HAL_LEASE_MONITOR_PB3;
    case 5U: return FURI_HAL_LEASE_MONITOR_PA4;
    case 6U: return FURI_HAL_LEASE_MONITOR_PA6;
    case 7U: return FURI_HAL_LEASE_MONITOR_PA7;
    default: return 0U;
    }
}
#endif

void labmate_monitor_gpio_release(LabMateApp* app, uint8_t index) {
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_LEASE_MONITOR_PA6)
    if(labmate_monitor_lease_handle == 0U) return;
    if(index >= GPIO_COUNT || index != labmate_monitor_lease_index ||
       labmate_monitor_lease_mask == 0U) {
        /* A caller's arbitrary capture pin is not our Monitor resource. */
        return;
    }
    /* Cleanup is permitted only while the owned lease remains held.
     * Retain a failed-release handle and never arm that pin again.
     */
    const GpioPin* pin = labmate_gpio_pins[index];
    furi_hal_gpio_init_simple(pin, GpioModeAnalog);
    app->monitor_active = false;
    if(furi_hal_resource_lease_release(
           labmate_monitor_lease_handle, labmate_monitor_lease_mask)) {
        labmate_monitor_lease_handle = 0U;
        labmate_monitor_lease_mask = 0U;
        labmate_monitor_lease_index = GPIO_COUNT;
        labmate_level_finish(
            &app->gpio_level_witness,index,true,
            furi_get_tick(),furi_kernel_get_tick_frequency());
    } else {
        labmate_level_invalidate(&app->gpio_level_witness);
        app->monitor_release_fault = true;
        app->monitor_blocked = true;
    }
#else
    (void)app;
    (void)index;
    /* No SDK lease: no GPIO write even on RELEASE. */
#endif
}

void labmate_monitor_gpio_activate(LabMateApp* app) {
    /* PA7 is never reconfigured while PWM is RUN, BUSY or unresolved. */
    const bool pa7_reserved =
        app->generator_running || app->generator_blocked ||
        app->generator_release_fault;
    app->gpio_index =
        labmate_monitor_entry_pin(app->gpio_index, pa7_reserved);
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_LEASE_MONITOR_PA6)
    if(app->monitor_release_fault || labmate_monitor_lease_handle != 0U) {
        app->monitor_blocked = true;
        return;
    }
    const uint32_t mask = labmate_monitor_mask(app->gpio_index);
    if(mask == 0U) {
        app->monitor_blocked = true;
        return;
    }
    const uint32_t handle = furi_hal_resource_lease_try_acquire(mask);
    if(handle == 0U) {
        app->monitor_blocked = true;
        return; /* Must not configure GPIO or sample unowned input. */
    }
    labmate_monitor_lease_handle = handle;
    labmate_monitor_lease_mask = mask;
    labmate_monitor_lease_index = app->gpio_index;
    const GpioPin* pin = labmate_gpio_pins[app->gpio_index];
    furi_hal_gpio_init_simple(pin, GpioModeInput);
    const bool level = furi_hal_gpio_read(pin);
    app->gpio_state = level;
    app->gpio_previous_state = level;
    app->monitor_active = true;
    app->monitor_blocked = false;
#else
    app->monitor_blocked = true; /* no unsafe old-SDK GPIO fallback */
#endif
}

/* False signifies unavailable sample, never an electrical LOW level. */
bool labmate_monitor_gpio_read(LabMateApp* app, uint8_t index, bool* level) {
    if(!app || !level || index >= GPIO_COUNT) return false;
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_LEASE_MONITOR_PA6)
    if(app->monitor_blocked || app->monitor_release_fault ||
       !app->monitor_active ||
       labmate_monitor_lease_handle == 0U ||
       labmate_monitor_lease_index != index) return false;
    *level = furi_hal_gpio_read(labmate_gpio_pins[index]);
    return true;
#else
    return false;
#endif
}
