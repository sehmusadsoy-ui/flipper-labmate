#include "labmate_comm_resource.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    LabMateCommOwner owner = LabMateCommNone;
    LabMateCommBusy b = {0};
    assert(!labmate_comm_local_claim(NULL, LabMateCommI2c3, b));
    assert(!labmate_comm_local_claim(&owner, LabMateCommNone, b));
    assert(labmate_comm_local_claim(&owner, LabMateCommI2c3, b));
    assert(!labmate_comm_local_claim(&owner, LabMateCommOneWirePa4, b));
    assert(!labmate_comm_local_release(&owner, LabMateCommOneWirePa4));
    assert(owner == LabMateCommI2c3);
    assert(labmate_comm_local_release(&owner, LabMateCommI2c3));
    assert(!labmate_comm_local_release(&owner, LabMateCommI2c3));

    LabMateCommBusy variants[] = {
        {.capture_active = true},
        {.gpio_monitor_active = true},
        {.pwm_active = true},
        {.uart_active = true},
        {.logger_active = true},
    };
    for(unsigned i = 0; i < sizeof(variants) / sizeof(*variants); ++i) {
        assert(!labmate_comm_local_claim(&owner, LabMateCommI2c3, variants[i]));
        assert(!labmate_comm_local_claim(&owner, LabMateCommOneWirePa4, variants[i]));
        assert(owner == LabMateCommNone);
    }
    assert(labmate_comm_local_claim(&owner, LabMateCommOneWirePa4, b));
    assert(!labmate_comm_local_claim(&owner, LabMateCommI2c3, b));
    assert(labmate_comm_local_release(&owner, LabMateCommOneWirePa4));
    assert(!labmate_comm_local_can_claim(LabMateCommI2c3, LabMateCommI2c3, b));
    puts("v1.8 COMM app-local I2C/1Wire mutual exclusion and failure rollback PASS");
    return 0;
}
