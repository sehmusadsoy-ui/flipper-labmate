#include "labmate_pulse_ui_state.h"
bool labmate_pulse_ui_live(
    bool native_irq_active, bool native_pulse_owner,
    bool blocked, bool release_fault) {
    return native_irq_active && native_pulse_owner && !blocked && !release_fault;
}
