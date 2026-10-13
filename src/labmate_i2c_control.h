#pragma once

#include "labmate_i2c_scan.h"
#include <stdbool.h>
#include <stdint.h>

/* HAL-free, event-driven lifecycle model. NOT a thread, hardware lock,
 * asynchronous cancellation implementation, or GPIO driver.
 *
 * IMPORTANT: A worker stuck in furi_hal_i2c_acquire(FuriWaitForever)
 * CANNOT receive cancellation or report acquire_done. This model therefore
 * stays AwaitAcquire (stop_requested=true) and forbids app teardown/restart.
 * Production bus integration is blocked until that hazard is solved.
 */
typedef enum {
    LabMateI2cControlIdle = 0,
    LabMateI2cControlAwaitAcquire,
    LabMateI2cControlScanning,
    LabMateI2cControlAwaitRelease,
    LabMateI2cControlFinished,
    LabMateI2cControlCancelled,
    LabMateI2cControlFailed,
} LabMateI2cControlState;

typedef enum {
    LabMateI2cProbeNoAck = 0,
    LabMateI2cProbeAck,
    LabMateI2cProbeError,
} LabMateI2cProbeResult;

typedef struct {
    LabMateI2cScan scan;
    uint32_t generation;
    LabMateI2cControlState state;
    bool stop_requested;
    bool bus_held;
    bool probe_inflight;
    bool error_pending;
} LabMateI2cControl;

/* Construction-time initialization ONLY. This zeros ownership bookkeeping;
 * NEVER call on a live worker or after a real acquire. It does not unlock,
 * stop, or release the physical bus. */
void labmate_i2c_control_reset(LabMateI2cControl* control);
/* Returns false while an acquire/scan/release from a previous run is live. */
bool labmate_i2c_control_start(LabMateI2cControl* control, uint32_t* token);
/* STOP is a request, not proof of cancellation, release, or worker exit. */
bool labmate_i2c_control_request_stop(LabMateI2cControl* control);
/* Result must come from the same generation, after physical acquire returns. */
bool labmate_i2c_control_acquire_done(
    LabMateI2cControl* control,
    uint32_t token,
    bool acquired);
/* A worker may issue a probe ONLY after a successful acquire result. */
bool labmate_i2c_control_next_probe(LabMateI2cControl* control, uint8_t* address7);
bool labmate_i2c_control_probe_done(
    LabMateI2cControl* control,
    uint32_t token,
    uint8_t address7,
    LabMateI2cProbeResult result);
/* Caller must have completed the actual HAL release before reporting done. */
bool labmate_i2c_control_release_done(LabMateI2cControl* control, uint32_t token);
bool labmate_i2c_control_active(const LabMateI2cControl* control);
