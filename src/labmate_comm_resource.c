#include "labmate_comm_resource.h"

bool labmate_comm_local_can_claim(
    LabMateCommOwner current, LabMateCommOwner requested, LabMateCommBusy busy) {
    if(current != LabMateCommNone) return false;
    if(requested != LabMateCommI2c3 && requested != LabMateCommOneWirePa4)
        return false;
    return !busy.capture_active && !busy.gpio_monitor_active &&
           !busy.pwm_active && !busy.uart_active && !busy.logger_active;
}

bool labmate_comm_local_claim(
    LabMateCommOwner* current, LabMateCommOwner requested, LabMateCommBusy busy) {
    if(!current || !labmate_comm_local_can_claim(*current, requested, busy))
        return false;
    *current = requested;
    return true;
}

bool labmate_comm_local_release(
    LabMateCommOwner* current, LabMateCommOwner stopping) {
    if(!current || stopping == LabMateCommNone || *current != stopping)
        return false;
    *current = LabMateCommNone;
    return true;
}
