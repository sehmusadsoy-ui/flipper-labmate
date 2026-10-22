#pragma once
/* A Pulse LIVE indicator is justified only by successful native ownership,
 * an active IRQ and no blocked/release-fault state. No Flipper dependencies.
 */
#include <stdbool.h>
bool labmate_pulse_ui_live(
    bool native_irq_active, bool native_pulse_owner,
    bool blocked, bool release_fault);
