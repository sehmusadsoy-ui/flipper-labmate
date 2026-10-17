/* Real production adapter compiled against instrumented HAL/lease mocks.
 * E11 pins PC0+PC1 overlap GPIO Monitor/Pulse opt-in leases only.
 * No physical I2C ACK evidence or firmware-legacy-service arbitration.
 */
#include "labmate_i2c_momentum.h"
#include <furi_hal_i2c.h>
#include <furi_hal_resources.h>
#include <assert.h>
#include <stdio.h>

const FuriHalI2cBusHandle furi_hal_i2c_handle_external = {0x33U};
static unsigned acquires,releases,probes,claims,lease_releases;
static bool grant,stopping,lease_available=true,lease_release_ok=true;
static bool stop_on_acquire=false,hal_held=false,lease_held=false;
static uint8_t last_encoded;

uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
#ifdef LABMATE_TEST_LEASE_API
    assert(mask==FURI_HAL_LEASE_I2C3_EXT);
#else
    (void)mask;
#endif
    claims++;
    if(!lease_available || lease_held) return 0U;
    lease_held=true;
    return 19U;
}
bool furi_hal_resource_lease_release(uint32_t handle,uint32_t mask) {
#ifdef LABMATE_TEST_LEASE_API
    assert(handle==19U && mask==FURI_HAL_LEASE_I2C3_EXT);
#else
    (void)handle;(void)mask;
#endif
    assert(!hal_held);
    assert(lease_held);
    lease_releases++;
    if(!lease_release_ok) return false;
    lease_held=false;
    return true;
}
bool furi_hal_i2c_external_acquire_timeout(uint32_t t) {
    assert(t==LABMATE_I2C_ACQUIRE_TIMEOUT_MS && lease_held);
    acquires++;
    if(stop_on_acquire) stopping=true;
    if(!grant) return false;
    assert(!hal_held);
    hal_held=true;
    return true;
}
bool furi_hal_i2c_is_device_ready(
    const FuriHalI2cBusHandle* h,uint8_t a,uint32_t timeout_ms) {
    assert(h==&furi_hal_i2c_handle_external && hal_held && lease_held);
    assert(timeout_ms==LABMATE_I2C_PROBE_TIMEOUT_MS);
    assert(a>=0x10U && a<=0xEEU && !(a&1U));
    probes++;
    last_encoded=a;
    return a==(0x3CU<<1U);
}
void furi_hal_i2c_release(const FuriHalI2cBusHandle* h) {
    assert(h==&furi_hal_i2c_handle_external);
    assert(hal_held && lease_held);
    releases++;
    hal_held=false;
}
static bool is_stopping(void* p) {
    assert(p==&stopping);
    return stopping;
}
static void clear_counts(void) {
    assert(!hal_held && !lease_held);
    acquires=releases=probes=claims=lease_releases=0U;
    last_encoded=0U;
    grant=true;
    stopping=false;
    stop_on_acquire=false;
    lease_available=true;
    lease_release_ok=true;
}

int main(void) {
    LabMateI2cControl control;
    LabMateI2cMomentum bridge={
        .stop_context=&stopping,
        .stop_requested=is_stopping,
    };
    LabMateI2cSessionOps ops=labmate_i2c_momentum_ops(&bridge);
    /* Deliberately violate the transport order: must never probe pins
     * without a matching prior firmware lease and acquired HAL mutex.
     */
    assert(ops.probe(ops.context,0x78U,LABMATE_I2C_PROBE_TIMEOUT_MS)==
           LabMateI2cProbeError);
    assert(probes==0U);
#if defined(LABMATE_MOMENTUM_TIMED_I2C_API) && defined(LABMATE_TEST_LEASE_API)
    assert(labmate_i2c_momentum_available());
    clear_counts();
    labmate_i2c_control_reset(&control);
    assert(labmate_i2c_session_execute(&control,&ops));
    assert(control.state==LabMateI2cControlFinished);
    assert(control.scan.stored_count==1U && control.scan.addresses[0]==0x3CU);
    assert(probes==LABMATE_I2C_ADDR_COUNT && last_encoded==0xEEU);
    assert(acquires==1U && releases==1U && claims==1U && lease_releases==1U);
    assert(bridge.lease_handle==0U && !bridge.release_fault && !lease_held);

    clear_counts();
    lease_available=false;
    labmate_i2c_control_reset(&control);
    assert(!labmate_i2c_session_execute(&control,&ops));
    assert(control.state==LabMateI2cControlBusy);
    assert(claims==1U && acquires==0U && probes==0U && releases==0U &&
           lease_releases==0U);

    clear_counts();
    grant=false;
    labmate_i2c_control_reset(&control);
    assert(!labmate_i2c_session_execute(&control,&ops));
    assert(control.state==LabMateI2cControlBusy);
    assert(claims==1U && lease_releases==1U && acquires==1U && releases==0U &&
           probes==0U);

    clear_counts();
    stopping=true;
    labmate_i2c_control_reset(&control);
    assert(labmate_i2c_session_execute(&control,&ops));
    assert(control.state==LabMateI2cControlCancelled);
    assert(claims==0U && acquires==0U && releases==0U);

    clear_counts();
    stop_on_acquire=true;
    labmate_i2c_control_reset(&control);
    assert(labmate_i2c_session_execute(&control,&ops));
    assert(control.state==LabMateI2cControlCancelled);
    assert(claims==1U && acquires==1U && probes==0U &&
           releases==1U && lease_releases==1U);
    assert(!bridge.release_fault);

    clear_counts();
    lease_release_ok=false;
    labmate_i2c_control_reset(&control);
    assert(labmate_i2c_session_execute(&control,&ops));
    assert(bridge.release_fault && bridge.lease_handle==19U && lease_held);
    assert(releases==1U && lease_releases==1U && !hal_held);
    unsigned claims_before=claims;
    labmate_i2c_control_reset(&control);
    assert(!labmate_i2c_session_execute(&control,&ops));
    assert(claims==claims_before && probes==LABMATE_I2C_ADDR_COUNT);
    /* A release-fault bridge is terminal: never reset its handle to
     * "fix" it; the real runtime converts the fault to FAILED. */
    puts("E11 I2C ACTUAL ADAPTER HOST PASS: PC0/PC1 lease, BUSY, STOP, stale fault.");
    puts("NO GPIO/physical fixture tests; firmware legacy owners still bypass.");
#else
    (void)clear_counts; /* compiled but intentionally not run in old SDK */
    assert(!labmate_i2c_momentum_available());
    labmate_i2c_control_reset(&control);
    assert(!labmate_i2c_session_execute(&control,&ops));
    assert(control.state==LabMateI2cControlBusy);
    assert(!acquires && !probes && !releases && !claims && !lease_releases);
    puts("E11 I2C unsupported SDK FAIL-CLOSED PASS: zero HAL and lease actions.");
#endif
    return 0;
}
