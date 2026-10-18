#pragma once
/* Pure-C final-app-exit gate. A PC1 callback may retain a pointer into the
 * heap-allocated LabMateApp scope_native member: never free the app unless
 * there is positive proof that no owned callback or native lease survives.
 */
#include <stdbool.h>
#include "labmate_scope_native.h"

bool labmate_scope_exit_storage_safe(const LabMateScopeNative* session);
