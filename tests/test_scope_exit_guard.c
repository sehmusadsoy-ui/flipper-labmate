/* Verify that only positively detached/released Scope sessions are
 * eligible for heap reclamation. Pure ISO C, no firmware dependencies.
 *
 * cc -std=c11 -Wall -Wextra -Werror -pedantic -Isrc \
 *   tests/test_scope_exit_guard.c src/labmate_scope_exit_guard.c \
 *   -o /tmp/test_scope_exit_guard
 * /tmp/test_scope_exit_guard
 */
#include <assert.h>
#include <stdio.h>
#include "labmate_scope_exit_guard.h"

int main(void) {
    LabMateScopeNative n = {0};
    assert(!labmate_scope_exit_storage_safe(NULL));
    assert(!labmate_scope_exit_storage_safe(&n)); /* init incomplete */
    n.session_initialized = true;
    assert(labmate_scope_exit_storage_safe(&n));

    n.irq_enabled = true; /* ISR may hold &app->scope_native */
    assert(!labmate_scope_exit_storage_safe(&n));
    n.irq_enabled = false;

    n.active = true;
    assert(!labmate_scope_exit_storage_safe(&n));
    n.active = false;

    n.owner.handle = 42U;
    n.owner.phase = LabMateScopeOwnerRunning;
    assert(!labmate_scope_exit_storage_safe(&n));
    n.owner.phase = LabMateScopeOwnerReleaseFault;
    n.owner.fault_cleanup_phase = LabMateScopeOwnerRunning;
    assert(!labmate_scope_exit_storage_safe(&n));

    n.owner.handle = 0U;
    n.owner.phase = LabMateScopeOwnerIdle;
    assert(!labmate_scope_exit_storage_safe(&n)); /* stale cleanup status */
    n.owner.fault_cleanup_phase = LabMateScopeOwnerIdle;
    assert(labmate_scope_exit_storage_safe(&n));

    n.fault_sticky = true;
    assert(!labmate_scope_exit_storage_safe(&n));
    n.fault_sticky = false;
    assert(labmate_scope_exit_storage_safe(&n));
    puts("scope safe final-exit guard regression: PASS");
    return 0;
}
