#include "labmate_i2c_session.h"

static bool labmate_i2c_session_cancel(const LabMateI2cSessionOps* ops) {
    return ops->stop_requested && ops->stop_requested(ops->context);
}

bool labmate_i2c_session_execute(
    LabMateI2cControl* control, const LabMateI2cSessionOps* ops) {
    if(!control || !ops || !ops->acquire_bounded || !ops->probe || !ops->release)
        return false;

    uint32_t generation = 0U;
    if(!labmate_i2c_control_start(control, &generation)) return false;

    if(labmate_i2c_session_cancel(ops)) {
        (void)labmate_i2c_control_request_stop(control);
        (void)labmate_i2c_control_acquire_done(control, generation, false);
        return control->state == LabMateI2cControlCancelled;
    }

    /* This operation is only safe if the supplied transport's implementation
     * of acquire_bounded is genuinely time-limited, including contention.
     * A worker plus GUI timeout alone DOES NOT make HAL acquire cancellable.
     */
    const bool acquired =
        ops->acquire_bounded(ops->context, LABMATE_I2C_ACQUIRE_TIMEOUT_MS);
    /* A STOP can arrive while firmware waits for the external mutex.
     * Account for it BEFORE reporting a failed bounded acquisition:
     * STOP+timeout is CANCELLED, not a spurious bus fault. If acquired,
     * acquire_done moves directly to AwaitRelease (no probe). */
    if(labmate_i2c_session_cancel(ops))
        (void)labmate_i2c_control_request_stop(control);
    if(!labmate_i2c_control_acquire_done(control, generation, acquired))
        return false;
    if(!acquired) return false;

    /* Fail closed if STOP arrived during the bounded acquisition. */
    if(labmate_i2c_session_cancel(ops))
        (void)labmate_i2c_control_request_stop(control);

    while(control->state == LabMateI2cControlScanning) {
        if(labmate_i2c_session_cancel(ops))
            (void)labmate_i2c_control_request_stop(control);
        if(control->state != LabMateI2cControlScanning) break;

        uint8_t address7 = 0U;
        uint8_t encoded_address = 0U;
        if(!labmate_i2c_control_next_probe(control, &address7) ||
           !labmate_i2c_address_encode(address7, &encoded_address)) {
            labmate_i2c_scan_error(&control->scan);
            control->error_pending = true;
            control->state = LabMateI2cControlAwaitRelease;
            break;
        }
        const LabMateI2cProbeResult result =
            ops->probe(ops->context, encoded_address, LABMATE_I2C_PROBE_TIMEOUT_MS);
        if(!labmate_i2c_control_probe_done(control, generation, address7, result)) {
            labmate_i2c_scan_error(&control->scan);
            control->error_pending = true;
            control->probe_inflight = false;
            control->state = LabMateI2cControlAwaitRelease;
            break;
        }
    }

    /* Release once and only once AFTER acquired, including STOP and faults. */
    ops->release(ops->context);
    if(!labmate_i2c_control_release_done(control, generation))
        return false;
    return control->state == LabMateI2cControlFinished ||
           control->state == LabMateI2cControlCancelled;
}
