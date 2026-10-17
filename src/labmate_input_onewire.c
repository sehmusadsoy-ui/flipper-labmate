#include "labmate_input_tools.h"
#include "labmate_onewire_hw.h"

/* Explicit, one-shot real DS18B20 measurement. This handler runs only
 * on the app thread with the existing UI mutex; never from a GPIO IRQ.
 */
void labmate_input_onewire(
    LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {
    UNUSED(work);
    if(event.key == InputKeyBack) {
        labmate_onewire_hw_stop(&app->thermometer);
        app->screen = LabMateScreenMenu;
        return;
    }
    if(event.key != InputKeyOk) return;
    if(app->thermometer.status == LabMateOneWireHwConverting) {
        labmate_onewire_hw_stop(&app->thermometer);
        return;
    }

    /* Conservative local owner checks for all other LabMate drivers.
     * Not a cross-firmware GPIO lease; physical device tests remain open.
     */
    const LabMateCommBusy busy = {
        .capture_active = app->capture_owner != LabMateCaptureNone ||
                          app->frequency_irq_active || app->frequency_hw_active ||
                          app->pulse_irq_active || app->counter_active ||
                          app->button_active,
        .gpio_monitor_active = false, /* cannot enter tool from GPIO screen */
        .pwm_active = app->generator_running,
        .uart_active = app->uart.active,
        .logger_active = app->logger_recording || app->logger_busy,
    };
    (void)labmate_onewire_hw_start(&app->thermometer, &app->comm_owner, busy);
}
