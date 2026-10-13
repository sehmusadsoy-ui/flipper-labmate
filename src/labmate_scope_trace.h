#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* v1.9 feasibility: pure, HAL-free SINGLE-CHANNEL DIGITAL event trace.
 * Input is an observed binary level plus monotonically advancing 32-bit
 * caller-defined ticks; this module NEVER reads GPIO or infers hidden edges.
 * Tick source calibration, pin ownership, trigger timing and ISR throughput
 * are NOT established by this code.
 */
#define LABMATE_SCOPE_MAX_EVENTS 128U
#define LABMATE_SCOPE_MAX_SPAN_TICKS UINT32_C(2147483647)

typedef enum {
    LabMateScopeTriggerImmediate = 0,
    LabMateScopeTriggerRising,
    LabMateScopeTriggerFalling,
    LabMateScopeTriggerEither,
} LabMateScopeTrigger;

typedef enum {
    LabMateScopeIdle = 0,
    LabMateScopeArmed,
    LabMateScopeRecording,
    LabMateScopeStopped,
    LabMateScopeOverflow,
    LabMateScopeFault,
} LabMateScopeState;

typedef enum {
    LabMateScopeFaultNone = 0,
    LabMateScopeFaultInvalidLevel,
    LabMateScopeFaultClock,
    LabMateScopeFaultSpan,
} LabMateScopeFaultReason;

typedef enum {
    LabMateScopeFeedInactive = 0,
    LabMateScopeFeedStale,
    LabMateScopeFeedIgnored,
    LabMateScopeFeedRecorded,
    LabMateScopeFeedTriggered,
    LabMateScopeFeedOverflow,
    LabMateScopeFeedFault,
} LabMateScopeFeedResult;

/* Offsets are measured in caller ticks from actual trigger.
 * Immediate mode includes first known level at offset zero.
 * Edge-trigger modes contain the TRIGGERED new level at offset zero
 * but intentionally have NO pre-trigger waveform/history.
 */
typedef struct {
    uint32_t offset_ticks;
    uint8_t level;
} LabMateScopeEvent;

typedef struct {
    LabMateScopeEvent events[LABMATE_SCOPE_MAX_EVENTS];
    uint32_t generation;
    uint32_t last_tick;
    uint32_t elapsed_ticks;  /* arm time until trigger; trace span thereafter */
    uint32_t missed_lower_bound; /* 1 if capacity crossed; NOT a total count */
    uint16_t event_count;
    uint8_t last_level;
    LabMateScopeTrigger trigger;
    LabMateScopeState state;
    LabMateScopeFaultReason fault_reason;
} LabMateScopeTrace;

/* Init once, and ONLY when no asynchronous producer is operating.
 * All calls require a serialized owner (NOT thread safe / ISR safe).
 */
void labmate_scope_trace_init(LabMateScopeTrace* trace);

/* Start fails without mutation on invalid params, during ARM/RECORD, or
 * when generation token exhausted. Output token is unchanged on failure.
 */
bool labmate_scope_trace_start(
    LabMateScopeTrace* trace,
    LabMateScopeTrigger trigger,
    uint8_t initial_level,
    uint32_t start_tick,
    uint32_t* out_generation);

/* Every feed needs the generation returned at start.
 * Consecutive samples must have an unambiguous forward delta of at most
 * INT32_MAX ticks (32-bit wrap permitted), and total observed arm/record
 * lifetime must stay <= INT32_MAX. Equal timestamps with opposite
 * levels are a FAULT, not a fabricated zero-duration pulse.
 * Only OBSERVED level changes create events. Full capacity freezes trace,
 * sets missed_lower_bound=1 on the FIRST omitted edge; no overwrite.
 */
LabMateScopeFeedResult labmate_scope_trace_feed(
    LabMateScopeTrace* trace,
    uint32_t generation,
    uint32_t tick,
    uint8_t level);

/* STOP from ARMED/RECORDING only, preserving data; overflow/fault persist.
 * Caller must separately establish actual hardware/worker quiescence.
 */
bool labmate_scope_trace_stop(LabMateScopeTrace* trace, uint32_t generation);
bool labmate_scope_trace_event_at(
    const LabMateScopeTrace* trace, uint16_t index, LabMateScopeEvent* output);
bool labmate_scope_trace_is_active(const LabMateScopeTrace* trace);
