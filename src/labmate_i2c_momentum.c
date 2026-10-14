#include "labmate_i2c_momentum.h"
#include <furi_hal_i2c.h>

/* A patched Momentum SDK advertises the exported timed-lock API.
 * Stock SDK builds remain a safe no-op without manual build flags. */
#if defined(FURI_HAL_I2C_HAS_EXTERNAL_ACQUIRE_TIMEOUT) && \
    !defined(LABMATE_MOMENTUM_TIMED_I2C_API)
#define LABMATE_MOMENTUM_TIMED_I2C_API 1
#endif

#ifdef LABMATE_MOMENTUM_TIMED_I2C_API
/* A missing exported symbol must fail linking; never fall back to an
 * unbounded lock or direct GPIO register manipulation. */
extern bool furi_hal_i2c_external_acquire_timeout(uint32_t timeout_ms);
#endif

static bool labmate_i2c_momentum_acquire(void* ctx, uint32_t timeout_ms) {
    if(!ctx) return false;
#ifdef LABMATE_MOMENTUM_TIMED_I2C_API
    return furi_hal_i2c_external_acquire_timeout(timeout_ms);
#else
    (void)timeout_ms;
    return false;
#endif
}

static LabMateI2cProbeResult
    labmate_i2c_momentum_probe(void* ctx, uint8_t address, uint32_t timeout_ms) {
    if(!ctx || address < 0x10U || address > 0xEEU || (address & 1U))
        return LabMateI2cProbeError;
#ifdef LABMATE_MOMENTUM_TIMED_I2C_API
    /* This is an actual read-only HAL transaction; NACK and an individual
     * transfer timeout both yield NOACK, never a fabricated device. */
    return furi_hal_i2c_is_device_ready(
               &furi_hal_i2c_handle_external, address, timeout_ms) ?
        LabMateI2cProbeAck : LabMateI2cProbeNoAck;
#else
    (void)timeout_ms;
    return LabMateI2cProbeError;
#endif
}

static void labmate_i2c_momentum_release(void* ctx) {
#ifdef LABMATE_MOMENTUM_TIMED_I2C_API
    if(ctx) furi_hal_i2c_release(&furi_hal_i2c_handle_external);
#else
    (void)ctx;
#endif
}

static bool labmate_i2c_momentum_stopping(void* ctx) {
    const LabMateI2cMomentum* transport = ctx;
    return transport && transport->stop_requested &&
           transport->stop_requested(transport->stop_context);
}

bool labmate_i2c_momentum_available(void) {
#ifdef LABMATE_MOMENTUM_TIMED_I2C_API
    return true;
#else
    return false;
#endif
}

LabMateI2cSessionOps labmate_i2c_momentum_ops(LabMateI2cMomentum* transport) {
    const LabMateI2cSessionOps ops = {
        .context = transport,
        .acquire_bounded = labmate_i2c_momentum_acquire,
        .probe = labmate_i2c_momentum_probe,
        .release = labmate_i2c_momentum_release,
        .stop_requested = labmate_i2c_momentum_stopping,
    };
    return ops;
}
