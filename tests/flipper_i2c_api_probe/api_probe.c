/* Development-only, compile/link ABI probe for Momentum SDK I2C exports.
 * No HAL I2C calls are executed, no GPIO is configured, no transfer occurs.
 * This file is intentionally NOT in LabMate's production src/ tree.
 */
#include <furi_hal_i2c.h>
#include <stdbool.h>
#include <stdint.h>

typedef struct {
    const FuriHalI2cBusHandle* external;
    void (*acquire)(const FuriHalI2cBusHandle*);
    void (*release)(const FuriHalI2cBusHandle*);
    bool (*ready)(const FuriHalI2cBusHandle*, uint8_t, uint32_t);
} LabMateI2cAbiSymbols;

/* Taking addresses forces the FAP linker to resolve the exact SDK exports.
 * Neither this struct nor the app entry point calls the bus functions.
 */
static const LabMateI2cAbiSymbols api_symbols = {
    .external = &furi_hal_i2c_handle_external,
    .acquire = furi_hal_i2c_acquire,
    .release = furi_hal_i2c_release,
    .ready = furi_hal_i2c_is_device_ready,
};
static const LabMateI2cAbiSymbols* volatile abi_witness;

int32_t labmate_i2c_api_probe_app(void* ctx) {
    (void)ctx;
    abi_witness = &api_symbols;
    return 0; /* Always exits without acquiring or scanning I2C. */
}
