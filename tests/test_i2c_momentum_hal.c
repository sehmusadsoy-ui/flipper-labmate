/* Test the exact production adapter with fake HAL. NOT a physical scan. */
#include "labmate_i2c_momentum.h"
#include <furi_hal_i2c.h>
#include <assert.h>
#include <stdio.h>

const FuriHalI2cBusHandle furi_hal_i2c_handle_external = {0x33U};
static unsigned acquires, releases, probes;
static bool grant, stopping;
static uint8_t last_encoded;

bool furi_hal_i2c_external_acquire_timeout(uint32_t t) {
    assert(t == LABMATE_I2C_ACQUIRE_TIMEOUT_MS);
    acquires++;
    return grant;
}
bool furi_hal_i2c_is_device_ready(
    const FuriHalI2cBusHandle* h, uint8_t a, uint32_t timeout_ms) {
    assert(h == &furi_hal_i2c_handle_external);
    assert(timeout_ms == LABMATE_I2C_PROBE_TIMEOUT_MS);
    assert(a >= 0x10U && a <= 0xEEU && !(a & 1U));
    probes++;
    last_encoded = a;
    return a == (0x3CU << 1U);
}
void furi_hal_i2c_release(const FuriHalI2cBusHandle* h) {
    assert(h == &furi_hal_i2c_handle_external);
    releases++;
}
static bool is_stopping(void* p) {
    assert(p == &stopping);
    return stopping;
}

int main(void) {
    LabMateI2cControl control;
    LabMateI2cMomentum bridge = {
        .stop_context = &stopping,
        .stop_requested = is_stopping,
    };
    LabMateI2cSessionOps ops = labmate_i2c_momentum_ops(&bridge);
#ifdef LABMATE_MOMENTUM_TIMED_I2C_API
    assert(labmate_i2c_momentum_available());
    grant = true;
    labmate_i2c_control_reset(&control);
    assert(labmate_i2c_session_execute(&control, &ops));
    assert(control.state == LabMateI2cControlFinished);
    assert(control.scan.stored_count == 1U);
    assert(control.scan.addresses[0] == 0x3CU);
    assert(probes == LABMATE_I2C_ADDR_COUNT);
    assert(last_encoded == 0xEEU);
    assert(acquires == 1U && releases == 1U);

    grant = false;
    labmate_i2c_control_reset(&control);
    assert(!labmate_i2c_session_execute(&control, &ops));
    assert(acquires == 2U && releases == 1U && probes == LABMATE_I2C_ADDR_COUNT);

    stopping = true;
    labmate_i2c_control_reset(&control);
    assert(labmate_i2c_session_execute(&control, &ops));
    assert(control.state == LabMateI2cControlCancelled);
    assert(acquires == 2U && releases == 1U);
    puts("I2C HAL bridge tests PASS (FAKE HAL, bounded API enabled)");
#else
    assert(!labmate_i2c_momentum_available());
    labmate_i2c_control_reset(&control);
    assert(!labmate_i2c_session_execute(&control, &ops));
    assert(control.state == LabMateI2cControlFailed);
    assert(!acquires && !probes && !releases);
    puts("I2C stock firmware API-unavailable fail-closed tests PASS (FAKE HAL)");
#endif
    return 0;
}
