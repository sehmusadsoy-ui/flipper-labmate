#pragma once
#include <stdbool.h>
#include <stdint.h>

/* Host-testable button contact filter. All timestamps are unsigned tick or
 * DWT-cycle snapshots. Stable output changes only after a quiet interval.
 * "Response" here means electrical first-edge-to-debounced-stable delay,
 * not human reaction time or the mechanical time before first contact.
 */
typedef struct {
    bool stable_level;
    bool raw_level;
    bool pending;
    uint32_t first_tick;
    uint32_t last_tick;
    uint32_t first_cycle;
    uint32_t last_cycle;
    uint16_t edges_in_transition;
    uint32_t presses;
    uint32_t releases;
    uint32_t rejected_glitches;
    uint32_t last_bounce_cycles;
    uint32_t last_settle_ticks;
    uint16_t last_bounce_edges;
    uint32_t last_hold_ticks;
    uint32_t pressed_tick;
    bool press_started;
} LabMateButtonState;

typedef struct {
    bool stable_level;
    bool pending;
    uint32_t presses;
    uint32_t releases;
    uint32_t rejected_glitches;
    uint32_t last_bounce_cycles;
    uint32_t last_settle_ticks;
    uint16_t last_bounce_edges;
    uint32_t last_hold_ticks;
} LabMateButtonStats;

void labmate_button_state_init(volatile LabMateButtonState* state, bool initial_level);
void labmate_button_edge(
    volatile LabMateButtonState* state, bool level, uint32_t tick, uint32_t cycle);
void labmate_button_poll(
    volatile LabMateButtonState* state, uint32_t tick, uint32_t quiet_ticks);
void labmate_button_snapshot(
    const volatile LabMateButtonState* state, LabMateButtonStats* snapshot);
