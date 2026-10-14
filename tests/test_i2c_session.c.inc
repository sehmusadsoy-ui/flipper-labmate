#include "labmate_i2c_session.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    uint32_t acquire_calls, release_calls, probe_calls, max_timeout;
    bool grant;
    bool cancel_early;
    bool cancel_during_acquire;
    uint8_t cancel_after;
    uint8_t fail_address;
    uint8_t seen[LABMATE_I2C_ADDR_COUNT];
} Fake;

static bool acquire(void* c, uint32_t timeout) {
    Fake* f = c;
    ++f->acquire_calls;
    assert(timeout == LABMATE_I2C_ACQUIRE_TIMEOUT_MS);
    f->max_timeout = timeout;
    return f->grant;
}
static LabMateI2cProbeResult probe(void* c, uint8_t a, uint32_t timeout) {
    Fake* f = c;
    assert(timeout == LABMATE_I2C_PROBE_TIMEOUT_MS);
    assert((a & 1U) == 0 && a >= 0x10U && a <= 0xEEU);
    const uint8_t address = (uint8_t)(a >> 1U);
    assert(address == 0x08U + f->probe_calls);
    f->seen[f->probe_calls++] = address;
    if(address == f->fail_address) return LabMateI2cProbeError;
    if(address == 0x20U || address == 0x3CU)
        return LabMateI2cProbeAck;
    return LabMateI2cProbeNoAck;
}
static void release(void* c) { ((Fake*)c)->release_calls++; }
static bool cancelled(void* c) {
    const Fake* f = c;
    return f->cancel_early ||
           (f->cancel_during_acquire && f->acquire_calls != 0U) ||
           (f->cancel_after != 0 && f->probe_calls >= f->cancel_after);
}
static LabMateI2cSessionOps ops(Fake* f) {
    LabMateI2cSessionOps o = {f, acquire, probe, release, cancelled};
    return o;
}

int main(void) {
    LabMateI2cControl control;
    Fake f;
    LabMateI2cSessionOps callbacks;

    memset(&f, 0, sizeof(f));
    f.grant = true;
    callbacks = ops(&f);
    labmate_i2c_control_reset(&control);
    assert(!labmate_i2c_session_execute(NULL, &callbacks));
    assert(!labmate_i2c_session_execute(&control, NULL));
    assert(labmate_i2c_session_execute(&control, &callbacks));
    assert(f.acquire_calls == 1U && f.release_calls == 1U);
    assert(f.probe_calls == LABMATE_I2C_ADDR_COUNT);
    assert(control.state == LabMateI2cControlFinished);
    assert(control.scan.total_found == 2U && control.scan.stored_count == 2U);
    assert(control.scan.addresses[0] == 0x20U && control.scan.addresses[1] == 0x3CU);
    assert(!control.bus_held && !control.probe_inflight);

    /* A bounded acquisition refusal does not probe or release unowned bus. */
    memset(&f, 0, sizeof(f));
    callbacks = ops(&f);
    labmate_i2c_control_reset(&control);
    assert(!labmate_i2c_session_execute(&control, &callbacks));
    assert(control.state == LabMateI2cControlBusy);
    assert(f.acquire_calls == 1U && !f.probe_calls && !f.release_calls);

    /* Cancellation before acquire touches zero hardware. */
    memset(&f, 0, sizeof(f));
    f.grant = true;
    f.cancel_early = true;
    callbacks = ops(&f);
    labmate_i2c_control_reset(&control);
    assert(labmate_i2c_session_execute(&control, &callbacks));
    assert(control.state == LabMateI2cControlCancelled);
    assert(!f.acquire_calls && !f.probe_calls && !f.release_calls);

    /* Stop during acquired scan retains results and releases exactly once. */
    memset(&f, 0, sizeof(f));
    f.grant = true;
    f.cancel_after = 26U; /* scan 0x08 through 0x21, including ACK at 0x20 */
    callbacks = ops(&f);
    labmate_i2c_control_reset(&control);
    assert(labmate_i2c_session_execute(&control, &callbacks));
    assert(control.state == LabMateI2cControlCancelled);
    assert(f.probe_calls == 26U && f.release_calls == 1U);
    assert(control.scan.scanned_count == 26U && control.scan.total_found == 1U);
    assert(!control.bus_held);

    /* A per-address bus fault must still release and show ERROR. */
    memset(&f, 0, sizeof(f));
    f.grant = true;
    f.fail_address = 0x28U;
    callbacks = ops(&f);
    labmate_i2c_control_reset(&control);
    assert(!labmate_i2c_session_execute(&control, &callbacks));
    assert(control.state == LabMateI2cControlFailed);
    assert(f.probe_calls == 33U && f.release_calls == 1U);
    assert(!control.bus_held);

    /* STOP while a contended, bounded mutex wait times out is CANCELLED,
     * not a misleading transport fault; no unowned bus is released. */
    memset(&f, 0, sizeof(f));
    f.cancel_during_acquire = true;
    callbacks = ops(&f);
    labmate_i2c_control_reset(&control);
    assert(labmate_i2c_session_execute(&control, &callbacks));
    assert(control.state == LabMateI2cControlCancelled);
    assert(f.acquire_calls == 1U && !f.probe_calls && !f.release_calls);
    assert(!control.bus_held && !control.probe_inflight);

    /* STOP can also race a SUCCESSFUL bounded acquisition: do not
     * probe, and release the newly owned bus exactly once. */
    memset(&f, 0, sizeof(f));
    f.cancel_during_acquire = true;
    f.grant = true;
    callbacks = ops(&f);
    labmate_i2c_control_reset(&control);
    assert(labmate_i2c_session_execute(&control, &callbacks));
    assert(control.state == LabMateI2cControlCancelled);
    assert(f.acquire_calls == 1U && !f.probe_calls && f.release_calls == 1U);
    assert(!control.bus_held && !control.probe_inflight);

    puts("I2C bounded transport lifecycle: ACK/STOP/BUSY/FAULT/release PASS (HOST ONLY)");
    return 0;
}
