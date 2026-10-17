#include "labmate_scope_buffer.h"

#include <limits.h>

static bool labmate_scope_trigger_valid(LabMateScopeTrigger trigger) {
    return trigger == LabMateScopeTriggerEither ||
           trigger == LabMateScopeTriggerRising ||
           trigger == LabMateScopeTriggerFalling;
}

static bool labmate_scope_trigger_matches(LabMateScopeTrigger trigger, bool high) {
    return trigger == LabMateScopeTriggerEither ||
           (trigger == LabMateScopeTriggerRising && high) ||
           (trigger == LabMateScopeTriggerFalling && !high);
}

static void labmate_scope_saturating_drop(LabMateScopeBuffer* scope) {
    if(scope->dropped_edges != UINT32_MAX) ++scope->dropped_edges;
}

bool labmate_scope_buffer_init(
    LabMateScopeBuffer* scope, LabMateScopeEdge* storage, size_t capacity) {
    if(!scope || !storage || !capacity || capacity > LABMATE_SCOPE_MAX_EDGES) {
        return false;
    }
    *scope = (LabMateScopeBuffer){
        .edges = storage,
        .capacity = (uint16_t)capacity,
        .state = LabMateScopeIdle,
    };
    return true;
}

bool labmate_scope_buffer_arm(
    LabMateScopeBuffer* scope, LabMateScopeTrigger trigger, bool initial_level) {
    if(!scope || !scope->edges || !scope->capacity ||
       scope->capacity > LABMATE_SCOPE_MAX_EDGES ||
       !labmate_scope_trigger_valid(trigger) ||
       (scope->state != LabMateScopeIdle &&
        scope->state != LabMateScopeStopped)) {
        return false;
    }

    scope->count = 0;
    scope->dropped_edges = 0;
    scope->last_tick = 0;
    scope->previous_level = initial_level;
    scope->overflowed = false;
    scope->timebase_error = false;
    scope->trigger = trigger;
    scope->state = LabMateScopeArmed;
    return true;
}

bool labmate_scope_buffer_push_edge(
    LabMateScopeBuffer* scope, uint32_t tick, bool level_after_edge) {
    if(!scope) return false;
    if(scope->state != LabMateScopeArmed &&
       scope->state != LabMateScopeRecording &&
       scope->state != LabMateScopeFull) return false;

    /* Only an actual level transition is a signal event. */
    if(level_after_edge == scope->previous_level) return false;
    scope->previous_level = level_after_edge;

    if(scope->state == LabMateScopeFull) {
        labmate_scope_saturating_drop(scope);
        return false;
    }

    if(scope->state == LabMateScopeArmed) {
        if(!labmate_scope_trigger_matches(scope->trigger, level_after_edge)) return false;
        scope->edges[0] = (LabMateScopeEdge){
            .tick = tick,
            .delta_ticks = 0,
            .high = level_after_edge,
        };
        scope->last_tick = tick;
        scope->count = 1;
        scope->state = LabMateScopeRecording;
        return true;
    }

    /* modulo subtraction accepts a short wrap of the 32-bit clock. A gap
     * >= 2^31 is ambiguous (out-of-order or too long): fail closed.
     * The calling driver MUST also enforce a timeout without edges, since
     * a full modulo counter wrap can otherwise be invisible here. */
    const uint32_t delta = tick - scope->last_tick;
    if(delta == 0U || delta > LABMATE_SCOPE_MAX_SAFE_DELTA) {
        scope->timebase_error = true;
        labmate_scope_saturating_drop(scope);
        scope->state = LabMateScopeError;
        return false;
    }
    if(scope->count >= scope->capacity) {
        scope->overflowed = true;
        labmate_scope_saturating_drop(scope);
        scope->state = LabMateScopeFull;
        return false;
    }

    scope->edges[scope->count] = (LabMateScopeEdge){
        .tick = tick,
        .delta_ticks = delta,
        .high = level_after_edge,
    };
    ++scope->count;
    scope->last_tick = tick;
    return true;
}

void labmate_scope_buffer_stop(LabMateScopeBuffer* scope) {
    if(!scope) return;
    if(scope->state != LabMateScopeIdle &&
       scope->state != LabMateScopeStopped) {
        scope->state = LabMateScopeStopped;
    }
}

LabMateScopeSnapshot labmate_scope_buffer_snapshot(const LabMateScopeBuffer* scope) {
    if(!scope) {
        return (LabMateScopeSnapshot){.state = LabMateScopeError, .timebase_error = true};
    }
    return (LabMateScopeSnapshot){
        .state = scope->state,
        .count = scope->count,
        .capacity = scope->capacity,
        .dropped_edges = scope->dropped_edges,
        .overflowed = scope->overflowed,
        .timebase_error = scope->timebase_error,
    };
}
