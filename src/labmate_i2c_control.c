#include "labmate_i2c_control.h"
#include <string.h>

bool labmate_i2c_control_active(const LabMateI2cControl* c) {
    return c->state == LabMateI2cControlAwaitAcquire ||
           c->state == LabMateI2cControlScanning ||
           c->state == LabMateI2cControlAwaitRelease;
}

void labmate_i2c_control_reset(LabMateI2cControl* c) {
    memset(c, 0, sizeof(*c));
    labmate_i2c_scan_reset(&c->scan);
    c->state = LabMateI2cControlIdle;
}

bool labmate_i2c_control_start(LabMateI2cControl* c, uint32_t* token) {
    if(!token || labmate_i2c_control_active(c) || c->bus_held) return false;
    uint32_t next = c->generation + 1U;
    if(next == 0U) next = 1U;
    labmate_i2c_scan_reset(&c->scan);
    c->generation = next;
    c->stop_requested = false;
    c->probe_inflight = false;
    c->error_pending = false;
    c->state = LabMateI2cControlAwaitAcquire;
    *token = next;
    return true;
}

bool labmate_i2c_control_request_stop(LabMateI2cControl* c) {
    if(!labmate_i2c_control_active(c)) return false;
    c->stop_requested = true;
    if(c->state == LabMateI2cControlScanning && !c->probe_inflight) {
        labmate_i2c_scan_cancel(&c->scan);
        c->state = LabMateI2cControlAwaitRelease;
    }
    /* AwaitAcquire remains pending: a blocking acquire is NOT canceled.
     * AwaitRelease remains pending until the worker actually releases. */
    return true;
}

bool labmate_i2c_control_acquire_done(LabMateI2cControl* c, uint32_t token, bool acquired) {
    if(!token || token != c->generation || c->state != LabMateI2cControlAwaitAcquire)
        return false;
    if(!acquired) {
        c->state = c->stop_requested ? LabMateI2cControlCancelled : LabMateI2cControlBusy;
        return true;
    }
    c->bus_held = true;
    if(c->stop_requested) {
        c->state = LabMateI2cControlAwaitRelease;
    } else {
        labmate_i2c_scan_begin(&c->scan);
        c->state = LabMateI2cControlScanning;
    }
    return true;
}

bool labmate_i2c_control_next_probe(LabMateI2cControl* c, uint8_t* address7) {
    if(c->state != LabMateI2cControlScanning || !c->bus_held ||
       c->stop_requested || c->probe_inflight) return false;
    if(!labmate_i2c_scan_next(&c->scan, address7)) return false;
    c->probe_inflight = true;
    return true;
}

bool labmate_i2c_control_probe_done(
    LabMateI2cControl* c,
    uint32_t token,
    uint8_t address7,
    LabMateI2cProbeResult result) {
    if(!token || token != c->generation || c->state != LabMateI2cControlScanning ||
       !c->bus_held || !c->probe_inflight || !c->scan.awaiting_result ||
       address7 != c->scan.pending_address ||
       (result != LabMateI2cProbeNoAck && result != LabMateI2cProbeAck &&
        result != LabMateI2cProbeError)) return false;

    c->probe_inflight = false;
    if(result == LabMateI2cProbeError) {
        labmate_i2c_scan_error(&c->scan);
        c->error_pending = true;
        c->state = LabMateI2cControlAwaitRelease;
        return true;
    }
    if(!labmate_i2c_scan_record(&c->scan, address7, result == LabMateI2cProbeAck))
        return false;

    if(c->stop_requested) {
        labmate_i2c_scan_cancel(&c->scan);
        c->state = LabMateI2cControlAwaitRelease;
    } else if(c->scan.status == LabMateI2cScanComplete) {
        c->state = LabMateI2cControlAwaitRelease;
    }
    return true;
}

bool labmate_i2c_control_release_done(LabMateI2cControl* c, uint32_t token) {
    if(!token || token != c->generation ||
       c->state != LabMateI2cControlAwaitRelease || !c->bus_held ||
       c->probe_inflight) return false;
    c->bus_held = false;
    if(c->error_pending) c->state = LabMateI2cControlFailed;
    else if(c->stop_requested) c->state = LabMateI2cControlCancelled;
    else if(c->scan.status == LabMateI2cScanComplete) c->state = LabMateI2cControlFinished;
    else c->state = LabMateI2cControlFailed;
    return true;
}
