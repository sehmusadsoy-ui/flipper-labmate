#pragma once
#include <stdbool.h>
#include <stdint.h>

/* HAL-FREE lifecycle MODEL only. No existing Momentum FAP-wide PB14
 * exclusive lease/arbiter has been verified. A future caller may not
 * claim AtomicLeaseAvailable until supported and independently proven.
 * These types do not acquire GPIO, transfer data or make a sensor reading.
 */
typedef enum {
    LabMateOneWirePinUnknown = 0,
    LabMateOneWirePinIbButtonPb14, /* dedicated 1-Wire test candidate ONLY */
    LabMateOneWirePinPc0,
    LabMateOneWirePinPc1,
    LabMateOneWirePinOther
} LabMateOneWirePin;

typedef enum {
    LabMateOneWireVoltageUnknown = 0,
    LabMateOneWireVoltageVerified3V3,
    LabMateOneWireVoltageUnsafe
} LabMateOneWireVoltage;

typedef enum {
    LabMateOneWireArbiterUnknown = 0,
    LabMateOneWireArbiterUnavailable,
    LabMateOneWireArbiterAtomicLeaseSupported /* FUTURE MOCK ONLY */
} LabMateOneWireArbiter;

typedef struct {
    LabMateOneWirePin pin;
    LabMateOneWireVoltage voltage;
    LabMateOneWireArbiter arbiter;
    bool capture_active;
    bool gpio_monitor_active;
    bool pwm_running;
    bool ibutton_active;
    bool rfid_active; /* RFID HAL can configure PB14 as iButton bus too. */
    bool expansion_connected;
    bool other_owner_unknown;
    bool auto_power_requested;
    bool parasite_power_requested;
} LabMateOneWireEnvironment;

typedef enum {
    LabMateOneWireGateNoArbiter = 0,
    LabMateOneWireGateUnsafeVoltage,
    LabMateOneWireGateUnsafePower,
    LabMateOneWireGateUnsupportedPin,
    LabMateOneWireGateResourceBusy,
    LabMateOneWireGateModelEligible
} LabMateOneWireGate;

LabMateOneWireGate labmate_onewire_environment_check(const LabMateOneWireEnvironment* env);

typedef enum {
    LabMateOneWireSessionIdle = 0,
    LabMateOneWireSessionAwaitLease,
    LabMateOneWireSessionReady,
    LabMateOneWireSessionAwaitOperation,
    LabMateOneWireSessionAwaitRelease,
    LabMateOneWireSessionCompleted,
    LabMateOneWireSessionCancelled,
    LabMateOneWireSessionFailed
} LabMateOneWireSessionState;

typedef struct {
    LabMateOneWireSessionState state;
    uint32_t generation; /* Reject stale worker events after restart. */
    bool stop_requested;
    bool lease_held;
    bool error_pending;
} LabMateOneWireSession;

/* Init ONCE before first begin; never reset while any async lease/worker
 * may exist, including AwaitLease (STOP does not prove lease released).
 * The model is single-thread-owned. UI must receive locked snapshots.
 */
void labmate_onewire_session_init(LabMateOneWireSession* session);

/* Model-only start. Requires environment proof, including a hypothetical
 * future atomic arbiter, which current Momentum does not provide.
 */
bool labmate_onewire_session_begin(
    LabMateOneWireSession* session,
    const LabMateOneWireEnvironment* env,
    uint32_t* generation);

/* STOP in AwaitLease cannot cancel an external pending grant by itself.
 * A late grant MUST transition to AwaitRelease before exit/restart.
 */
bool labmate_onewire_session_stop(LabMateOneWireSession* session);
bool labmate_onewire_session_lease_done(
    LabMateOneWireSession* session, uint32_t generation, bool granted);
bool labmate_onewire_session_operation_begin(LabMateOneWireSession* session);
bool labmate_onewire_session_operation_done(
    LabMateOneWireSession* session, uint32_t generation, bool succeeded);
bool labmate_onewire_session_finish(LabMateOneWireSession* session);
bool labmate_onewire_session_release_done(
    LabMateOneWireSession* session, uint32_t generation);
bool labmate_onewire_session_active(const LabMateOneWireSession* session);
bool labmate_onewire_session_can_exit(const LabMateOneWireSession* session);
