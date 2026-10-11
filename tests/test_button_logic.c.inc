#include "labmate_button_logic.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

int main(void) {
    LabMateButtonState state;
    LabMateButtonStats view;
    labmate_button_state_init(&state, true);
    labmate_button_poll(&state, 100U, 10U);
    assert(state.presses == 0U && state.stable_level);

    /* One clean press with a 10-tick quiet time. */
    labmate_button_edge(&state, false, 110U, 1000U);
    labmate_button_edge(&state, false, 111U, 1001U); /* duplicate IRQ ignored */
    labmate_button_poll(&state, 119U, 10U);
    assert(state.presses == 0U);
    labmate_button_poll(&state, 120U, 10U);
    assert(state.presses == 1U && !state.stable_level);
    assert(state.last_bounce_edges == 0U);
    assert(state.last_bounce_cycles == 0U && state.last_settle_ticks == 10U);

    /* Released contact oscillates for 3 edges; last HIGH is stable. */
    labmate_button_edge(&state, true, 130U, 2000U);
    labmate_button_edge(&state, false, 132U, 2100U);
    labmate_button_edge(&state, true, 134U, 2300U);
    labmate_button_poll(&state, 143U, 10U);
    assert(state.releases == 0U);
    labmate_button_poll(&state, 144U, 10U);
    assert(state.releases == 1U && state.stable_level);
    assert(state.last_bounce_edges == 2U && state.last_bounce_cycles == 300U);
    assert(state.last_settle_ticks == 14U && state.last_hold_ticks == 24U);

    /* A brief LOW-HIGH glitch never becomes a stable press. */
    labmate_button_edge(&state, false, 160U, 2500U);
    labmate_button_edge(&state, true, 161U, 2550U);
    labmate_button_poll(&state, 171U, 10U);
    assert(state.rejected_glitches == 1U && state.presses == 1U);
    assert(state.last_bounce_cycles == 300U);

    /* 32-bit kernel ticks and DWT cycles wrap correctly inside the window. */
    labmate_button_state_init(&state, true);
    labmate_button_edge(&state, false, UINT32_MAX - 3U, UINT32_MAX - 7U);
    labmate_button_edge(&state, true, UINT32_MAX - 1U, UINT32_MAX - 2U);
    labmate_button_edge(&state, false, 1U, 3U);
    labmate_button_poll(&state, 9U, 10U);
    assert(state.presses == 0U);
    labmate_button_poll(&state, 11U, 10U);
    assert(state.presses == 1U && state.last_bounce_edges == 2U);
    assert(state.last_bounce_cycles == 11U);
    assert(state.last_settle_ticks == 15U);
    labmate_button_snapshot(&state, &view);
    assert(view.presses == 1U && !view.stable_level && !view.pending);

    /* Pending bounce is not promoted when the quiet-time setting is zero. */
    labmate_button_state_init(&state, true);
    labmate_button_edge(&state, false, 20U, 10U);
    labmate_button_poll(&state, 100U, 0U);
    assert(state.presses == 0U);

    puts("Button Analyzer pure bounce/settle/glitch/wrap tests PASS");
    return 0;
}
