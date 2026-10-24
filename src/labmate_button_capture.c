#include "labmate_button_capture.h"
#include "labmate_button_logic.h"
#include "labmate_capture_core.h"
#include "labmate_capture_exti.h"
#include "labmate_resource_policy.h"
#include <furi_hal.h>
#include <furi_hal_resources.h>
#include <limits.h>

/* Silence needed after the final electrical transition before a contact is
 * considered stable. No claim to measure finger-to-first-contact latency.
 */
static const uint8_t quiet_ms[] = {5U, 10U, 20U, 50U};

/* Experimental E11: the same physical PC1/EXTI1 lease as LOW frequency.
 * No callback registration on an unpatched SDK (fail closed).
 */
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK)
static uint32_t labmate_button_lease_handle;
static void labmate_button_irq(void* context) {
    LabMateApp* app = context;
    if(!app->button_active || app->capture_owner != LabMateCaptureButton) return;
    const GpioPin* pin = labmate_gpio_pins[app->capture_pin_index];
    labmate_button_edge(
        &app->button_irq, furi_hal_gpio_read(pin), furi_get_tick(), DWT->CYCCNT);
}
#endif /* experimental matched Momentum ABI */

void labmate_button_capture_reset(LabMateApp* app) {
    if(app->button_active) return;
    app->button_session_started = false;
    labmate_button_state_init(&app->button_irq, true);
    labmate_button_snapshot(&app->button_irq, &app->button_stats);
    app->button_bounce_us = 0U;
    app->button_settle_ms = 0U;
    app->button_hold_ms = 0U;
}

void labmate_button_capture_change_quiet(LabMateApp* app, int8_t direction) {
    if(app->button_active || direction == 0) return;
    if(direction > 0 && app->button_quiet_index < 3U) ++app->button_quiet_index;
    if(direction < 0 && app->button_quiet_index > 0U) --app->button_quiet_index;
    app->button_quiet_ms = quiet_ms[app->button_quiet_index];
}

void labmate_button_capture_start(LabMateApp* app) {
    if(app->button_active ||
       !labmate_capture_can_start(app, LabMateCaptureButton)) return;
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK)
    if(labmate_button_lease_handle != 0U) {
        app->capture_blocked = true;
        return;
    }
    const GpioPin* pin = labmate_gpio_pins[app->gpio_index];
    const uint32_t handle =
        furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PC1);
    if(handle == 0U) {
        app->capture_blocked = true;
        return; /* GPIO and EXTI remain unchanged */
    }
    labmate_button_lease_handle = handle;
    /* TRY-ADD has no GPIO mode side effect on refusal: legacy callback
     * ownership is respected even if its driver does not use the lease.
     */
    if(!furi_hal_gpio_try_add_int_callback(pin, labmate_button_irq, app)) {
        if(furi_hal_resource_lease_release(
               labmate_button_lease_handle, FURI_HAL_LEASE_IRQ_PC1)) {
            labmate_button_lease_handle = 0U;
        } else {
            app->capture_release_fault = true;
        }
        app->capture_blocked = true;
        return;
    }
    furi_hal_gpio_disable_int_callback(pin);
    /* Internal pull-up: contact to GND => LOW. Configure only after
     * both lease and callback slot have been successfully acquired.
     */
    furi_hal_gpio_init(pin, GpioModeInterruptRiseFall, GpioPullUp, GpioSpeedVeryHigh);
    const bool resume = app->button_session_started;
    const bool current_level = furi_hal_gpio_read(pin);
    if(resume) {
        labmate_button_state_resume(&app->button_irq, current_level);
    } else {
        labmate_button_state_init(&app->button_irq, current_level);
        app->button_bounce_us = 0U;
        app->button_settle_ms = 0U;
        app->button_hold_ms = 0U;
    }
    labmate_button_snapshot(&app->button_irq, &app->button_stats);
    app->capture_pin_index = app->gpio_index;
    app->capture_owner = LabMateCaptureButton;
    app->button_session_started = true;
    app->button_active = true;
    furi_hal_gpio_enable_int_callback(pin);
#else
    app->capture_blocked = true; /* no unsafe legacy callback fallback */
#endif
}

void labmate_button_capture_poll(LabMateApp* app) {
    if(!app->button_active || app->capture_owner != LabMateCaptureButton) return;
    const uint32_t hz = furi_kernel_get_tick_frequency();
    const uint32_t quiet = hz == 0U ? 1U :
        (uint32_t)(((uint64_t)app->button_quiet_ms * hz + 999U) / 1000U);
    const uint32_t now = furi_get_tick();

    /* ISR may update the raw edge series independently of the UI mutex. */
    FURI_CRITICAL_ENTER();
    labmate_button_poll(&app->button_irq, now, quiet == 0U ? 1U : quiet);
    labmate_button_snapshot(&app->button_irq, &app->button_stats);
    FURI_CRITICAL_EXIT();

    const uint64_t bounce_us = pulse_cycles_to_us(app->button_stats.last_bounce_cycles);
    app->button_bounce_us = bounce_us > UINT32_MAX ? UINT32_MAX : (uint32_t)bounce_us;
    if(hz > 0U) {
        app->button_settle_ms =
            (uint32_t)((uint64_t)app->button_stats.last_settle_ticks * 1000U / hz);
        app->button_hold_ms =
            (uint32_t)((uint64_t)app->button_stats.last_hold_ticks * 1000U / hz);
    }
}

void labmate_button_capture_stop(LabMateApp* app) {
    if(!app->button_active) return;
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK)
    if(labmate_button_lease_handle == 0U) {
        app->capture_blocked = true;
        return; /* do not tear down an unowned GPIO */
    }
    const GpioPin* pin = labmate_gpio_pins[app->capture_pin_index];
    furi_hal_gpio_disable_int_callback(pin);
    furi_hal_gpio_remove_int_callback(pin);
    labmate_capture_exti_clear((uint32_t)pin->pin, true);
    furi_hal_gpio_init_simple(pin, GpioModeAnalog);
    app->button_active = false;
    if(furi_hal_resource_lease_release(
           labmate_button_lease_handle, FURI_HAL_LEASE_IRQ_PC1)) {
        labmate_button_lease_handle = 0U;
        /* Do not advertise a free PC1 before firmware acknowledges release. */
        if(app->capture_owner == LabMateCaptureButton) {
            app->capture_owner =
                labmate_capture_owner_after_stop(app->capture_owner, LabMateCaptureButton);
            app->capture_pin_index = GPIO_COUNT;
        }
    } else {
        app->capture_release_fault = true;
        app->capture_blocked = true; /* retain failed-release lease */
    }
#else
    app->capture_blocked = true;
#endif
}

bool labmate_button_lease_pending(void) {
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK)
    return labmate_button_lease_handle != 0U;
#else
    return false;
#endif
}
