#pragma once
/* v1.9 experimental single-channel PC1 Scope UI integration.
 * All entry points are application-thread only and called under app mutex,
 * except teardown after the main loop. Never execute these from GPIO IRQ.
 */
#include <input/input.h>
#include "labmate_internal.h"

bool labmate_scope_bridge_init(LabMateApp* app);
void labmate_scope_bridge_enter(LabMateApp* app);
void labmate_scope_bridge_poll(LabMateApp* app);
void labmate_scope_bridge_input(LabMateApp* app, InputEvent event);
/* Returns false on unfinished native lease/IRQ teardown. */
bool labmate_scope_bridge_stop(LabMateApp* app);
