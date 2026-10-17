#include "labmate_i2c_momentum.h"
#include <furi_hal_i2c.h>
#include <furi_hal_resources.h>

/* A patched Momentum SDK advertises the exported timed-lock API.
 * Stock SDK builds remain a safe no-op without manual build flags. */
#if defined(FURI_HAL_I2C_HAS_EXTERNAL_ACQUIRE_TIMEOUT) && \
    !defined(LABMATE_MOMENTUM_TIMED_I2C_API)
#define LABMATE_MOMENTUM_TIMED_I2C_API 1
#endif

/* The patched furi_hal_i2c.h (or the host HAL stub) declares the
 * timeout API. Do not redeclare it: Momentum compiles with -Werror and
 * -Wredundant-decls. A missing firmware export must still fail FAP
 * linking; never fall back to unbounded locking or direct GPIO access. */

/* The timed HAL mutex is necessary but protects only clients using that
 * same I2C3 HAL bus. The separate E11 lease overlaps Monitor/IRQ PC0/PC1
 * claims. Both APIs must be present, otherwise no hardware access.
 * Independent legacy firmware services may still bypass E11 leases.
 */
static bool labmate_i2c_momentum_acquire(void* ctx, uint32_t timeout_ms) {
    if(!ctx) return false;
#if defined(LABMATE_MOMENTUM_TIMED_I2C_API) && \
    defined(FURI_HAL_RESOURCE_LEASE_API_V1)
    LabMateI2cMomentum* bridge = ctx;
    if(bridge->lease_handle || bridge->release_fault) return false;
    const uint32_t handle =
        furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_I2C3_EXT);
    if(handle == 0U) return false; /* no HAL mutex, probes or GPIO change */
    bridge->lease_handle = handle;
    if(furi_hal_i2c_external_acquire_timeout(timeout_ms)) return true;

    /* HAL mutex was NOT acquired; release only our lease. */
    if(!furi_hal_resource_lease_release(
           bridge->lease_handle, FURI_HAL_LEASE_I2C3_EXT)) {
        bridge->release_fault = true;
    } else {
        bridge->lease_handle = 0U;
    }
    return false;
#else
    (void)timeout_ms;
    return false;
#endif
}

static LabMateI2cProbeResult
    labmate_i2c_momentum_probe(void* ctx, uint8_t address, uint32_t timeout_ms) {
    if(!ctx || address < 0x10U || address > 0xEEU || (address & 1U))
        return LabMateI2cProbeError;
#if defined(LABMATE_MOMENTUM_TIMED_I2C_API) && \
    defined(FURI_HAL_RESOURCE_LEASE_API_V1)
    const LabMateI2cMomentum* bridge = ctx;
    if(!bridge->lease_handle || bridge->release_fault)
        return LabMateI2cProbeError;
    /* Only the worker holding its pin+bus lease may issue HAL probes.
     * NACK and HAL transfer timeout both yield NOACK, not a fake ACK. */
    return furi_hal_i2c_is_device_ready(
               &furi_hal_i2c_handle_external, address, timeout_ms) ?
        LabMateI2cProbeAck : LabMateI2cProbeNoAck;
#else
    (void)timeout_ms;
    return LabMateI2cProbeError;
#endif
}

static void labmate_i2c_momentum_release(void* ctx) {
#if defined(LABMATE_MOMENTUM_TIMED_I2C_API) && \
    defined(FURI_HAL_RESOURCE_LEASE_API_V1)
    LabMateI2cMomentum* bridge = ctx;
    if(!bridge || !bridge->lease_handle || bridge->release_fault) return;
    /* HAL mutex/pins are released before surrendering the GPIO lease. */
    furi_hal_i2c_release(&furi_hal_i2c_handle_external);
    if(furi_hal_resource_lease_release(
           bridge->lease_handle, FURI_HAL_LEASE_I2C3_EXT)) {
        bridge->lease_handle = 0U;
    } else {
        bridge->release_fault = true;
        /* Deliberate leaked handle prevents unsafe future claims. */
    }
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
#if defined(LABMATE_MOMENTUM_TIMED_I2C_API) && \
    defined(FURI_HAL_RESOURCE_LEASE_API_V1)
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
