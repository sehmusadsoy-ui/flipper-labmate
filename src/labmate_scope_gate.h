#pragma once
/* Pure host-testable PC1 ownership gate. NO native IRQ, GPIO or FAP wiring.
 * Native lease + try_add_callback MUST succeed before actual pin writes.
 */
#include <stdbool.h>
#include <stdint.h>
#include "labmate_resource_policy.h"
#include "labmate_comm_resource.h"

typedef enum {
    LabMateScopeGateReady = 0,
    LabMateScopeGateBusy,
    LabMateScopeGateUnsupported,
    LabMateScopeGateFault,
    LabMateScopeGateInvalid,
} LabMateScopeGate;

typedef struct {
    uint8_t selected_pin;
    LabMateCaptureOwner capture_owner;
    LabMateCommOwner comm_owner;
    bool frequency_irq_active, frequency_hw_active, pulse_irq_active;
    bool counter_active, button_active, monitor_active, logger_active, uart_active;
    bool capture_release_fault, monitor_release_fault;
    bool firmware_lease_api, firmware_try_callback;
} LabMateScopePc1Environment;

typedef enum {
    LabMateScopeOwnerIdle = 0,
    LabMateScopeOwnerLease,
    LabMateScopeOwnerCallback,
    LabMateScopeOwnerPinConfigured,
    LabMateScopeOwnerRunning,
    LabMateScopeOwnerReleaseFault,
} LabMateScopeOwnerPhase;

typedef struct {
    LabMateScopeOwnerPhase phase;
    LabMateScopeOwnerPhase fault_cleanup_phase; /* last confirmed owned resources */
    bool callback_detached; /* confirmed, never remove foreign callback twice */
    bool pin_restored;      /* confirmed, never touch foreign pin twice */
    uint32_t handle; /* nonzero only after successful native lease acquire */
} LabMateScopeOwnerState;

typedef struct {
    bool detach_callback, restore_pin, release_lease;
} LabMateScopeReleasePlan;

LabMateScopeGate labmate_scope_gate_pc1(
    const LabMateScopePc1Environment* env, const LabMateScopeOwnerState* state);
/* All transition functions ONLY record *confirmed native effects*; they do
 * not invoke firmware. A refused request never performs any HAL operation. */
bool labmate_scope_owner_lease_acquired(LabMateScopeOwnerState* state, uint32_t handle);
bool labmate_scope_owner_callback_added(LabMateScopeOwnerState* state);
bool labmate_scope_owner_pin_configured(LabMateScopeOwnerState* state);
bool labmate_scope_owner_started(LabMateScopeOwnerState* state);
LabMateScopeReleasePlan labmate_scope_owner_stop_plan(const LabMateScopeOwnerState* state);
/* On incomplete teardown, retain handle and latch FAULT (fail closed).
 * A release plan is a model only; real IRQ must be disabled/quiesced first. */
bool labmate_scope_owner_stop_confirmed(
    LabMateScopeOwnerState* state, bool callback_removed,
    bool pin_restored, bool lease_released);
