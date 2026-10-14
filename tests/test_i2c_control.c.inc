/* Pure worker/UI lifecycle tests. NO Furi/HAL/I2C hardware calls. */
#include "labmate_i2c_control.h"
#include <assert.h>
#include <stdio.h>

static void test_stop_during_blocked_acquire(void) {
    LabMateI2cControl c;
    uint32_t token = 0U, retry = 0U;
    uint8_t a = 0U;
    labmate_i2c_control_reset(&c);
    assert(c.state == LabMateI2cControlIdle);
    assert(!labmate_i2c_control_start(&c, NULL));
    assert(labmate_i2c_control_start(&c, &token) && token != 0U);
    assert(c.state == LabMateI2cControlAwaitAcquire);
    assert(!c.bus_held && !labmate_i2c_control_next_probe(&c, &a));
    assert(!labmate_i2c_control_start(&c, &retry));
    assert(!labmate_i2c_control_release_done(&c, token));
    assert(labmate_i2c_control_request_stop(&c));
    assert(c.stop_requested && c.state == LabMateI2cControlAwaitAcquire);
    assert(labmate_i2c_control_active(&c));
    assert(!labmate_i2c_control_start(&c, &retry));
    /* User STOP does not cancel a real HAL FuriWaitForever wait. */
    assert(!labmate_i2c_control_acquire_done(&c, token+1U, true));
    assert(c.state == LabMateI2cControlAwaitAcquire);
    assert(labmate_i2c_control_acquire_done(&c, token, true));
    assert(c.bus_held && c.state == LabMateI2cControlAwaitRelease);
    assert(c.scan.scanned_count == 0U);
    assert(!labmate_i2c_control_next_probe(&c, &a));
    assert(!labmate_i2c_control_start(&c, &retry));
    /* Ownership persists until the worker reports actual release. */
    assert(labmate_i2c_control_release_done(&c, token));
    assert(!c.bus_held && c.state == LabMateI2cControlCancelled);
    assert(!labmate_i2c_control_release_done(&c, token));
    assert(labmate_i2c_control_start(&c, &retry));
    assert(retry != token);
    assert(!labmate_i2c_control_acquire_done(&c, token, true));
    assert(labmate_i2c_control_acquire_done(&c, retry, false));
    assert(c.state == LabMateI2cControlBusy && !c.bus_held);
    assert(!labmate_i2c_control_active(&c));
}

static void test_acquire_denied_after_stop(void) {
    LabMateI2cControl c;
    uint32_t token;
    labmate_i2c_control_reset(&c);
    assert(labmate_i2c_control_start(&c, &token));
    assert(labmate_i2c_control_request_stop(&c));
    assert(labmate_i2c_control_acquire_done(&c, token, false));
    assert(c.state == LabMateI2cControlCancelled && !c.bus_held);
    assert(!labmate_i2c_control_request_stop(&c));
}

static void test_full_scan_and_release(void) {
    LabMateI2cControl c;
    uint32_t token;
    uint8_t addr;
    labmate_i2c_control_reset(&c);
    assert(labmate_i2c_control_start(&c, &token));
    assert(labmate_i2c_control_acquire_done(&c, token, true));
    assert(c.state == LabMateI2cControlScanning && c.bus_held);
    for(unsigned i=LABMATE_I2C_FIRST_ADDR; i<=LABMATE_I2C_LAST_ADDR; ++i) {
        assert(labmate_i2c_control_next_probe(&c, &addr) && addr == i);
        assert(!labmate_i2c_control_next_probe(&c, &addr));
        assert(!labmate_i2c_control_probe_done(&c, token+1U, addr, LabMateI2cProbeAck));
        uint8_t wrong=(uint8_t)(addr == 0x77U ? addr-1U : addr+1U);
        assert(!labmate_i2c_control_probe_done(&c, token, wrong, LabMateI2cProbeAck));
        const LabMateI2cProbeResult result =
            (i==0x20U || i==0x3CU || i==0x68U) ? LabMateI2cProbeAck : LabMateI2cProbeNoAck;
        assert(labmate_i2c_control_probe_done(&c, token, addr, result));
        assert(!labmate_i2c_control_probe_done(&c, token, addr, result));
    }
    assert(c.state == LabMateI2cControlAwaitRelease && c.bus_held);
    assert(c.scan.scanned_count == LABMATE_I2C_ADDR_COUNT);
    assert(c.scan.total_found == 3U && c.scan.stored_count == 3U);
    assert(c.scan.addresses[0] == 0x20U && c.scan.addresses[1] == 0x3CU);
    assert(c.scan.addresses[2] == 0x68U);
    assert(!labmate_i2c_control_next_probe(&c, &addr));
    assert(!labmate_i2c_control_release_done(&c, token+1U));
    assert(labmate_i2c_control_release_done(&c, token));
    assert(c.state == LabMateI2cControlFinished && !c.bus_held);
    assert(!labmate_i2c_control_release_done(&c, token));
}

static void test_cancel_during_inflight_probe(void) {
    LabMateI2cControl c;
    uint8_t a;
    uint32_t token;
    labmate_i2c_control_reset(&c);
    assert(labmate_i2c_control_start(&c, &token));
    assert(labmate_i2c_control_acquire_done(&c, token, true));
    assert(labmate_i2c_control_next_probe(&c, &a) && a == 0x08U);
    assert(labmate_i2c_control_request_stop(&c));
    assert(c.state == LabMateI2cControlScanning);
    assert(c.probe_inflight && c.bus_held && c.stop_requested);
    assert(!labmate_i2c_control_next_probe(&c, &a));
    assert(!labmate_i2c_control_release_done(&c, token));
    assert(labmate_i2c_control_probe_done(&c, token, a, LabMateI2cProbeAck));
    assert(c.state == LabMateI2cControlAwaitRelease);
    assert(c.scan.status == LabMateI2cScanCancelled);
    assert(c.scan.scanned_count == 1U && c.scan.total_found == 1U);
    assert(!labmate_i2c_control_next_probe(&c, &a));
    assert(labmate_i2c_control_release_done(&c, token));
    assert(c.state == LabMateI2cControlCancelled && !c.bus_held);
}

static void test_cancel_between_probes(void) {
    LabMateI2cControl c;
    uint32_t token;
    uint8_t a;
    labmate_i2c_control_reset(&c);
    assert(labmate_i2c_control_start(&c, &token));
    assert(labmate_i2c_control_acquire_done(&c, token, true));
    assert(labmate_i2c_control_request_stop(&c));
    assert(c.state == LabMateI2cControlAwaitRelease);
    assert(c.scan.status == LabMateI2cScanCancelled && !c.probe_inflight);
    assert(!labmate_i2c_control_next_probe(&c, &a));
    assert(labmate_i2c_control_release_done(&c, token));
    assert(c.state == LabMateI2cControlCancelled);
}

static void test_probe_error_and_restart(void) {
    LabMateI2cControl c;
    uint32_t token, next;
    uint8_t a;
    labmate_i2c_control_reset(&c);
    assert(labmate_i2c_control_start(&c, &token));
    assert(labmate_i2c_control_acquire_done(&c, token, true));
    assert(labmate_i2c_control_next_probe(&c, &a));
    assert(!labmate_i2c_control_probe_done(&c, token, a, (LabMateI2cProbeResult)99));
    assert(!labmate_i2c_control_probe_done(&c, token, a, (LabMateI2cProbeResult)-1));
    assert(c.probe_inflight);
    assert(labmate_i2c_control_probe_done(&c, token, a, LabMateI2cProbeError));
    assert(c.state == LabMateI2cControlAwaitRelease && c.bus_held);
    assert(c.scan.status == LabMateI2cScanError && c.error_pending);
    assert(!labmate_i2c_control_start(&c, &next));
    assert(labmate_i2c_control_release_done(&c, token));
    /* A real probe fault is ERROR, not mutex contention BUSY. */
    assert(c.state == LabMateI2cControlFailed && !c.bus_held);
    assert(labmate_i2c_control_start(&c, &next) && next != token);
    assert(c.scan.scanned_count == 0U && !c.stop_requested);
    assert(labmate_i2c_control_acquire_done(&c, next, false));
    assert(c.state == LabMateI2cControlBusy && !c.bus_held);
}

int main(void) {
    test_stop_during_blocked_acquire();
    test_acquire_denied_after_stop();
    test_full_scan_and_release();
    test_cancel_during_inflight_probe();
    test_cancel_between_probes();
    test_probe_error_and_restart();
    puts("I2C lifecycle model: pending-acquire STOP, ownership, scan/release, in-flight cancel, stale events, error/restart PASS (HOST ONLY)");
    return 0;
}
