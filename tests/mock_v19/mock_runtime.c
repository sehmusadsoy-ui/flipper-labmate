#include "mock_runtime.h"
#include "furi_hal_resources.h"
#include "labmate_capture_exti.h"
#include <assert.h>
#include <string.h>

LabMateMockHal labmate_mock_hal;
LabMateMockDwt labmate_mock_dwt;
uint32_t SystemCoreClock;
const GpioPin gpio_ext_pc1 = {.pin = 2U};

void labmate_mock_reset(void) {
    memset(&labmate_mock_hal, 0, sizeof(labmate_mock_hal));
    memset(&labmate_mock_dwt, 0, sizeof(labmate_mock_dwt));
    labmate_mock_dwt.CTRL = DWT_CTRL_CYCCNTENA_Msk;
    SystemCoreClock = UINT32_C(64000000);
}
void labmate_mock_critical_enter(void) {++labmate_mock_hal.critical_depth;}
void labmate_mock_critical_exit(void) {
    assert(labmate_mock_hal.critical_depth > 0U);
    --labmate_mock_hal.critical_depth;
}
bool furi_hal_gpio_read(const GpioPin* pin) {
    assert(pin == &gpio_ext_pc1);
    return labmate_mock_hal.input_level;
}
bool furi_hal_gpio_try_add_int_callback(
    const GpioPin* pin, void (*callback)(void*), void* context) {
    assert(pin == &gpio_ext_pc1);
    if(labmate_mock_hal.foreign_callback || labmate_mock_hal.callback) return false;
    labmate_mock_hal.callback = callback;
    labmate_mock_hal.callback_context = context;
    labmate_mock_hal.callback_enabled = true;
    return true;
}
void furi_hal_gpio_disable_int_callback(const GpioPin* pin) {
    assert(pin == &gpio_ext_pc1);
    labmate_mock_hal.callback_enabled = false;
}
void furi_hal_gpio_enable_int_callback(const GpioPin* pin) {
    assert(pin == &gpio_ext_pc1);
    assert(labmate_mock_hal.callback);
    labmate_mock_hal.callback_enabled = true;
}
void furi_hal_gpio_remove_int_callback(const GpioPin* pin) {
    assert(pin == &gpio_ext_pc1);
    assert(labmate_mock_hal.callback && !labmate_mock_hal.callback_enabled);
    ++labmate_mock_hal.callback_removes;
    labmate_mock_hal.callback = NULL;
    labmate_mock_hal.callback_context = NULL;
}
void furi_hal_gpio_init(
    const GpioPin* pin, GpioMode mode, GpioPull pull, GpioSpeed speed) {
    assert(pin == &gpio_ext_pc1 && mode == GpioModeInterruptRiseFall);
    (void)pull;
    (void)speed;
    ++labmate_mock_hal.gpio_writes;
}
void furi_hal_gpio_init_simple(const GpioPin* pin, GpioMode mode) {
    assert(pin == &gpio_ext_pc1 && mode == GpioModeAnalog);
    ++labmate_mock_hal.gpio_writes;
}
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
    assert(mask == FURI_HAL_LEASE_IRQ_PC1);
    if(labmate_mock_hal.lease_occupied || labmate_mock_hal.held_handle)
        return 0U;
    labmate_mock_hal.held_handle = 5U;
    return 5U;
}
bool furi_hal_resource_lease_release(uint32_t handle, uint32_t mask) {
    assert(mask == FURI_HAL_LEASE_IRQ_PC1);
    assert(handle == 5U && labmate_mock_hal.held_handle == handle);
    ++labmate_mock_hal.lease_releases;
    if(labmate_mock_hal.refuse_release) return false;
    labmate_mock_hal.held_handle = 0U;
    return true;
}
void labmate_capture_exti_clear(uint32_t line, bool clear_rising) {
    assert(line == UINT32_C(0x2));
    (void)clear_rising;
    ++labmate_mock_hal.exti_writes;
}
void labmate_mock_edge(uint32_t tick, bool high) {
    labmate_mock_dwt.CYCCNT = tick;
    labmate_mock_hal.input_level = high;
    if(labmate_mock_hal.callback_enabled && labmate_mock_hal.callback)
        labmate_mock_hal.callback(labmate_mock_hal.callback_context);
}
