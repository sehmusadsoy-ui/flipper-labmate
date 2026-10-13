#include "labmate_i2c_present.h"
#include <string.h>

static LabMateI2cViewStatus labmate_i2c_view_resolve(const LabMateI2cControl* c) {
    switch(c->state) {
    case LabMateI2cControlIdle: return LabMateI2cViewNotScanned;
    case LabMateI2cControlAwaitAcquire:
        return c->stop_requested ? LabMateI2cViewStopPending : LabMateI2cViewWaitBus;
    case LabMateI2cControlScanning:
        return c->stop_requested ? LabMateI2cViewStopPending : LabMateI2cViewScanning;
    case LabMateI2cControlAwaitRelease: return LabMateI2cViewReleasing;
    case LabMateI2cControlFinished:
        return c->scan.total_found == 0U ? LabMateI2cViewNoDevices : LabMateI2cViewResults;
    case LabMateI2cControlCancelled: return LabMateI2cViewCancelled;
    case LabMateI2cControlFailed: return LabMateI2cViewFailed;
    default: return LabMateI2cViewFailed;
    }
}

bool labmate_i2c_present(const LabMateI2cControl* c, uint8_t requested, LabMateI2cView* out) {
    if(!c || !out) return false;
    memset(out, 0, sizeof(*out));
    out->status = labmate_i2c_view_resolve(c);
    out->requested_page = requested;
    out->scanned_count = c->scan.scanned_count;
    out->found_total = c->scan.total_found;

    /* Do not trust a corrupt count to index outside the 16-byte buffer. */
    const uint8_t stored = c->scan.stored_count > LABMATE_I2C_RESULT_CAP ?
        LABMATE_I2C_RESULT_CAP : c->scan.stored_count;
    out->stored_count = stored;
    out->truncated = c->scan.total_found > stored;
    out->page_count = (uint8_t)(
        stored ? (stored + LABMATE_I2C_VIEW_ROWS - 1U) / LABMATE_I2C_VIEW_ROWS : 1U);
    out->page = requested >= out->page_count ?
        (uint8_t)(out->page_count - 1U) : requested;

    const uint8_t first = (uint8_t)(out->page * LABMATE_I2C_VIEW_ROWS);
    for(uint8_t i = first; i < stored && out->row_count < LABMATE_I2C_VIEW_ROWS; ++i) {
        out->row_address[out->row_count++] = c->scan.addresses[i];
    }

    /* Logical state only; physical app exit additionally requires worker
     * join and proof that its HAL-acquire function returned. */
    out->model_quiescent = !labmate_i2c_control_active(c) && !c->bus_held;
    return true;
}

const char* labmate_i2c_view_status_text(LabMateI2cViewStatus status) {
    switch(status) {
    case LabMateI2cViewNotScanned: return "NOT SCANNED";
    case LabMateI2cViewWaitBus: return "WAIT BUS";
    case LabMateI2cViewStopPending: return "STOP PENDING";
    case LabMateI2cViewScanning: return "SCANNING";
    case LabMateI2cViewReleasing: return "RELEASING";
    case LabMateI2cViewResults: return "RESULTS";
    case LabMateI2cViewNoDevices: return "NO DEVICES";
    case LabMateI2cViewCancelled: return "CANCELLED";
    case LabMateI2cViewFailed: return "ERROR";
    default: return "ERROR";
    }
}
