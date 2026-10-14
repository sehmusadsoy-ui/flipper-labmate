#pragma once
#include "labmate_comm_resource.h"
#include "labmate_i2c_present.h"
#include <stdbool.h>
#include <stdint.h>

typedef struct LabMateI2cRuntime LabMateI2cRuntime;

typedef enum {
    LabMateI2cRuntimeReady = 0,
    LabMateI2cRuntimeApiMissing,
    LabMateI2cRuntimeBusy,
    LabMateI2cRuntimeScanning,
    LabMateI2cRuntimeResults,
    LabMateI2cRuntimeNoDevices,
    LabMateI2cRuntimeCancelled,
    LabMateI2cRuntimeFailed,
} LabMateI2cRuntimeStatus;

/* Worker owns HAL bus, never the GUI/input callback. Every public method is
 * main-thread-owned except the internally mutex-guarded stop callback.
 * Actual scans require the matching timed-I2C firmware API; stock FAP
 * fails closed with ApiMissing and never touches PC0/PC1.
 */
LabMateI2cRuntime* labmate_i2c_runtime_alloc(void);
bool labmate_i2c_runtime_start(
    LabMateI2cRuntime* state, LabMateCommOwner* owner, LabMateCommBusy busy);
void labmate_i2c_runtime_poll(LabMateI2cRuntime* state);
void labmate_i2c_runtime_stop(LabMateI2cRuntime* state);
void labmate_i2c_runtime_free(LabMateI2cRuntime* state);
LabMateI2cRuntimeStatus labmate_i2c_runtime_snapshot(
    LabMateI2cRuntime* state, uint8_t page, LabMateI2cView* view);
