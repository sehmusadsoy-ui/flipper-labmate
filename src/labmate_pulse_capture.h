#pragma once
#include "labmate_internal.h"

/* Pulse-specific EXTI lifecycle. Active pin identity remains fixed until
 * the IRQ callback is detached and the EXTI triggers have been cleared.
 */
void labmate_pulse_capture_start(LabMateApp* app);
void labmate_pulse_capture_stop(LabMateApp* app);

/* True while Pulse still retains any E11 EXTI lease token/mask. */
bool labmate_pulse_lease_pending(void);
