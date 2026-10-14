#include "labmate_button_logic.h"
#include <limits.h>

void labmate_button_state_init(volatile LabMateButtonState* state, bool initial_level) {
    LabMateButtonState reset = {0};
    reset.stable_level = initial_level;
    reset.raw_level = initial_level;
    *state = reset;
}

void labmate_button_state_resume(volatile LabMateButtonState* state, bool initial_level) {
    /* No IRQ is armed while this state transition occurs. Preserve cumulative
     * counts and completed metrics, but do not count edges or elapsed hold
     * time across an inactive STOP interval. */
    state->stable_level = initial_level;
    state->raw_level = initial_level;
    state->pending = false;
    state->first_tick = 0U;
    state->last_tick = 0U;
    state->first_cycle = 0U;
    state->last_cycle = 0U;
    state->edges_in_transition = 0U;
    state->pressed_tick = 0U;
    state->press_started = false;
}

void labmate_button_edge(
    volatile LabMateButtonState* state, bool level, uint32_t tick, uint32_t cycle) {
    if(level == state->raw_level) return;
    if(!state->pending) {
        state->first_tick = tick;
        state->first_cycle = cycle;
        state->edges_in_transition = 0U;
        state->pending = true;
    }
    if(state->edges_in_transition < UINT16_MAX) ++state->edges_in_transition;
    state->raw_level = level;
    state->last_tick = tick;
    state->last_cycle = cycle;
}

void labmate_button_poll(
    volatile LabMateButtonState* state, uint32_t tick, uint32_t quiet_ticks) {
    if(!state->pending || quiet_ticks == 0U ||
       (uint32_t)(tick - state->last_tick) < quiet_ticks) return;

    state->pending = false;
    if(state->raw_level == state->stable_level) {
        if(state->rejected_glitches < UINT32_MAX) ++state->rejected_glitches;
        return;
    }

    state->stable_level = state->raw_level;
    state->last_bounce_cycles = state->last_cycle - state->first_cycle;
    state->last_settle_ticks = tick - state->first_tick;
    state->last_bounce_edges = state->edges_in_transition > 0U ?
        (uint16_t)(state->edges_in_transition - 1U) : 0U;

    /* PC1 uses an internal pull-up, so LOW means contact closed / pressed. */
    if(!state->stable_level) {
        if(state->presses < UINT32_MAX) ++state->presses;
        state->pressed_tick = tick;
        state->press_started = true;
    } else {
        if(state->releases < UINT32_MAX) ++state->releases;
        if(state->press_started) {
            state->last_hold_ticks = tick - state->pressed_tick;
            state->press_started = false;
        }
    }
}

void labmate_button_snapshot(
    const volatile LabMateButtonState* state, LabMateButtonStats* out) {
    out->stable_level = state->stable_level;
    out->pending = state->pending;
    out->presses = state->presses;
    out->releases = state->releases;
    out->rejected_glitches = state->rejected_glitches;
    out->last_bounce_cycles = state->last_bounce_cycles;
    out->last_settle_ticks = state->last_settle_ticks;
    out->last_bounce_edges = state->last_bounce_edges;
    out->last_hold_ticks = state->last_hold_ticks;
}
