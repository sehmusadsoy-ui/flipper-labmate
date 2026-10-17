#pragma once

/* LabMate v1.9 digital Logic Scope: allocation-free timestamp buffer.
 *
 * Pure ISO C, intentionally NO GPIO/HAL/IRQ acquisition or UI wiring here.
 * Calling code must acquire an exclusive firmware-owned input/EXTI lease
 * before arming and detach its own IRQ before stop/re-arm or freeing storage.
 * push_edge() has one IRQ writer; ALL reader/control operations must exclude
 * that IRQ using the platform's correct critical section. An application
 * mutex alone does not serialize a hardware interrupt.
 */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define LABMATE_SCOPE_MAX_EDGES 256U
#define LABMATE_SCOPE_MAX_SAFE_DELTA UINT32_C(0x7fffffff)

typedef enum {
    LabMateScopeIdle = 0,
    LabMateScopeArmed,
    LabMateScopeRecording,
    LabMateScopeFull,
    LabMateScopeError,
    LabMateScopeStopped,
} LabMateScopeState;

typedef enum {
    LabMateScopeTriggerEither = 0,
    LabMateScopeTriggerRising,
    LabMateScopeTriggerFalling,
} LabMateScopeTrigger;

typedef struct {
    uint32_t tick;       /* unmodified 32-bit counter value at the edge */
    uint32_t delta_ticks;/* elapsed since preceding STORED edge; zero for trigger */
    bool high;           /* input level following this observed transition */
} LabMateScopeEdge;

typedef struct {
    LabMateScopeEdge* edges; /* caller-owned array, not stack-local in Flipper */
    uint16_t capacity;
    uint16_t count;
    uint32_t dropped_edges; /* saturation at UINT32_MAX */
    uint32_t last_tick;
    bool previous_level;
    bool overflowed;
    bool timebase_error;
    LabMateScopeTrigger trigger;
    LabMateScopeState state;
} LabMateScopeBuffer;

typedef struct {
    LabMateScopeState state;
    uint16_t count;
    uint16_t capacity;
    uint32_t dropped_edges;
    bool overflowed;
    bool timebase_error;
} LabMateScopeSnapshot;

/* init() returns false for NULL or capacity outside 1..256 and never writes
 * the edge array. Caller must ensure IRQ is NOT running during init(). */
bool labmate_scope_buffer_init(
    LabMateScopeBuffer* scope, LabMateScopeEdge* storage, size_t capacity);

/* Start/re-arm after a confirmed resource lease AND a completed owned-IRQ
 * teardown (only from IDLE/STOPPED); initializes the input's previous
 * sampled level, but stores no fictitious edge. A rejected trigger or state
 * leaves the existing scope unchanged. */
bool labmate_scope_buffer_arm(
    LabMateScopeBuffer* scope, LabMateScopeTrigger trigger, bool initial_level);

/* IRQ-side ONLY once the app has successfully installed its own callback.
 * Returns true only when one real edge is stored. Non-triggering edges,
 * duplicate-level callbacks, overflow and invalid timebase return false.
 * Missing/ambiguous timebase intervals >= 2^31 ticks enter sticky ERROR;
 * 32-bit modulo subtraction handles a single short hardware counter wrap.
 * Counter periods >= 2^32 ticks cannot be disambiguated by this module:
 * the caller MUST enforce a separate bounded capture timeout. */
bool labmate_scope_buffer_push_edge(
    LabMateScopeBuffer* scope, uint32_t tick, bool level_after_edge);

/* Caller must detach owned IRQ (and exclude any in-flight callback) before
 * invoking stop(). Keeps recorded edges and sticky fault indicators. */
void labmate_scope_buffer_stop(LabMateScopeBuffer* scope);

/* Caller must exclude the writer IRQ for the entire copy AND for reading
 * elements of scope->edges[0..count). No dynamic memory is allocated. */
LabMateScopeSnapshot labmate_scope_buffer_snapshot(const LabMateScopeBuffer* scope);
