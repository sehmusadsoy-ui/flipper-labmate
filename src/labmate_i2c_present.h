#pragma once

#include "labmate_i2c_control.h"
#include <stdbool.h>
#include <stdint.h>

/* Pure read-only presentation snapshot for the future 128x64 UI.
 * NO Canvas, HAL, GPIO, bus acquire, threads, or real-device scan.
 * Never label an unrun or incomplete scan as "NO DEVICES".
 */
#define LABMATE_I2C_VIEW_ROWS 4U

typedef enum {
    LabMateI2cViewNotScanned = 0,
    LabMateI2cViewWaitBus,
    LabMateI2cViewStopPending,
    LabMateI2cViewScanning,
    LabMateI2cViewReleasing,
    LabMateI2cViewResults,
    LabMateI2cViewNoDevices,
    LabMateI2cViewCancelled,
    LabMateI2cViewFailed,
} LabMateI2cViewStatus;

typedef struct {
    LabMateI2cViewStatus status;
    uint8_t requested_page;
    uint8_t page;
    uint8_t page_count;
    uint8_t row_count;
    uint8_t row_address[LABMATE_I2C_VIEW_ROWS];
    uint8_t scanned_count;
    uint8_t found_total;
    uint8_t stored_count;
    bool truncated;
    /* Logical model only: does NOT establish real worker exit or HAL release. */
    bool model_quiescent;
} LabMateI2cView;

/* Builds a bounded, non-mutating snapshot from a single-thread-owned model.
 * Later firmware integration MUST synchronize worker-to-UI state transfer. */
bool labmate_i2c_present(const LabMateI2cControl* control, uint8_t page, LabMateI2cView* out);

/* Labels deliberately short enough for narrow UI badges. */
const char* labmate_i2c_view_status_text(LabMateI2cViewStatus status);
