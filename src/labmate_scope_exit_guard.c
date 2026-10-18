#include "labmate_scope_exit_guard.h"

bool labmate_scope_native_reinit_safe(const LabMateScopeNative* session) {
    return session && !session->active && !session->irq_enabled &&
           !session->fault_sticky && session->owner.handle == 0U &&
           !session->owner.callback_detached &&
           !session->owner.pin_restored &&
           session->owner.phase == LabMateScopeOwnerIdle &&
           session->owner.fault_cleanup_phase == LabMateScopeOwnerIdle;
}

bool labmate_scope_exit_storage_safe(const LabMateScopeNative* session) {
    return session && session->session_initialized &&
           labmate_scope_native_reinit_safe(session);
}
