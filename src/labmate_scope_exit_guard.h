#pragma once
/* Pure-C final-app-exit gate. A PC1 callback may retain a pointer into the
 * heap-allocated LabMateApp scope_native member: never free the app unless
 * there is positive proof that no owned callback or native lease survives.
 */
#include <stdbool.h>
#include "labmate_scope_native.h"

/* Reinitialization may erase owner bookkeeping. Require complete idle
 * ownership before allowing native_init() to reset the state. */
bool labmate_scope_native_reinit_safe(const LabMateScopeNative* session);

/* A full STOP/BACK must also prove LabMate's shared capture owner no
 * longer claims Scope (another legitimate owner is not modified here). */
bool labmate_scope_native_stop_confirmed(
    const LabMateScopeNative* session, LabMateCaptureOwner shared_owner);

bool labmate_scope_exit_storage_safe(const LabMateScopeNative* session);
