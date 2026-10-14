#include "labmate_input_tools.h"
#include "labmate_i2c_runtime.h"

/* True bounded-acquire scan only after explicit OK.
 * Standard Momentum firmware lacks the timed acquisition export, so the
 * same production FAP fails closed and never touches PC0/PC1.
 */
void labmate_input_i2c(
    LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {
    UNUSED(work);
    if(event.key == InputKeyBack) {
        labmate_i2c_runtime_stop(app->i2c);
        app->screen = LabMateScreenMenu;
        return;
    }

    if(event.key == InputKeyUp || event.key == InputKeyDown) {
        LabMateI2cView view;
        (void)labmate_i2c_runtime_snapshot(app->i2c, app->i2c_page, &view);
        const uint8_t count = view.page_count > 0U ? view.page_count : 1U;
        if(event.key == InputKeyDown)
            app->i2c_page = (uint8_t)((app->i2c_page + 1U) % count);
        else
            app->i2c_page = (uint8_t)((app->i2c_page + count - 1U) % count);
        return;
    }

    if(event.key != InputKeyOk) return;

    LabMateI2cView view;
    const LabMateI2cRuntimeStatus status =
        labmate_i2c_runtime_snapshot(app->i2c, app->i2c_page, &view);
    if(status == LabMateI2cRuntimeScanning) {
        labmate_i2c_runtime_stop(app->i2c);
        return;
    }

    const LabMateCommBusy busy = {
        .capture_active = app->capture_owner != LabMateCaptureNone ||
                          app->frequency_irq_active || app->frequency_hw_active ||
                          app->pulse_irq_active || app->counter_active ||
                          app->button_active,
        .gpio_monitor_active = false, /* only reachable through main menu */
        .pwm_active = app->generator_running,
        .uart_active = app->uart.active,
        .logger_active = app->logger_recording || app->logger_busy,
    };
    app->i2c_page = 0U;
    (void)labmate_i2c_runtime_start(app->i2c, &app->comm_owner, busy);
}
