#include "labmate_scope_plot.h"
#include <assert.h>
#include <stdio.h>
#include <stdint.h>

static void focus_real_100_hz(void) {
    LabMateScopeEdge edges[64] = {0};
    LabMateScopePlotLine drawn[LABMATE_SCOPE_PLOT_MAX_LINES] = {0};
    /* At 1 MHz test clock: each edge 5 ms, i.e. 100 Hz at 50% duty. */
    for(uint16_t i = 0; i < 64; ++i) {
        edges[i].tick = 1000U + (uint32_t)i * 5000U;
        edges[i].delta_ticks = i ? 5000U : 0U;
        edges[i].high = (i & 1U) == 0U;
    }
    LabMateScopePlotStats s = labmate_scope_plot_focus(
        edges, 64U, false, drawn, LABMATE_SCOPE_PLOT_MAX_LINES);
    assert(s.result == LabMateScopePlotReady);
    assert(s.visible_edges == 13U);
    assert(s.line_count == 24U);
    assert(s.cropped_old_edges);
    assert(s.window_cycles == 60000U); /* six actual cycles, no synthetic data */
    assert(drawn[0].x0 == LABMATE_SCOPE_PLOT_X_LEFT);
    assert(drawn[s.line_count-1].x1 == LABMATE_SCOPE_PLOT_X_RIGHT);
    /* At 100Hz, a half-period now spans ~10 pixels, not <=2px. */
    for(uint16_t k = 0U; k < s.line_count; k += 2U) {
        assert(drawn[k].x1 - drawn[k].x0 >= 9U);
        assert(drawn[k].y0 == LABMATE_SCOPE_PLOT_Y_HIGH ||
               drawn[k].y0 == LABMATE_SCOPE_PLOT_Y_LOW);
        assert(drawn[k].y0 <= 35U && drawn[k].y1 <= 35U);
        assert(drawn[k+1].y0 <= 35U && drawn[k+1].y1 <= 35U);
    }
    assert(LABMATE_SCOPE_PLOT_Y_LOW < 41U); /* no glyph overlap */
    /* The source buffer is unchanged; displayed window starts at edge 51. */
    assert(edges[51].tick == 256000U);
    assert(edges[63].tick == 316000U);
}
/* A real-edge 1 kHz signal with 40% HIGH / 60% LOW MUST keep the
 * observed duty asymmetry in a 13-edge focus viewport. This checks
 * visualization geometry only; it is not Flipper hardware calibration. */
static void focus_nonideal_1khz(void) {
    LabMateScopeEdge edges[64] = {0};
    LabMateScopePlotLine drawn[LABMATE_SCOPE_PLOT_MAX_LINES] = {0};
    edges[0].tick = 250U;
    edges[0].high = true;
    /* One simulated MHz tick clock: 400us HIGH, 600us LOW. */
    for(uint16_t i = 1U; i < 64U; ++i) {
        const uint32_t interval = edges[i - 1U].high ? 400U : 600U;
        edges[i].tick = edges[i - 1U].tick + interval;
        edges[i].delta_ticks = interval;
        edges[i].high = !edges[i - 1U].high;
    }
    const LabMateScopePlotStats s = labmate_scope_plot_focus(
        edges, 64U, false, drawn, LABMATE_SCOPE_PLOT_MAX_LINES);
    assert(s.result == LabMateScopePlotReady);
    assert(s.visible_edges == 13U && s.line_count == 24U);
    assert(s.window_cycles == 6000U && s.cropped_old_edges);
    assert(drawn[0].x0 == LABMATE_SCOPE_PLOT_X_LEFT);
    assert(drawn[s.line_count - 1U].x1 == LABMATE_SCOPE_PLOT_X_RIGHT);
    uint16_t high_count = 0U, low_count = 0U;
    for(uint16_t k = 0U; k < s.line_count; k += 2U) {
        const LabMateScopePlotLine horizontal = drawn[k];
        const uint8_t width = horizontal.x1 - horizontal.x0;
        assert(horizontal.x1 > horizontal.x0);
        assert(horizontal.y0 == horizontal.y1);
        assert(drawn[k + 1U].x0 == horizontal.x1);
        if(horizontal.y0 == LABMATE_SCOPE_PLOT_Y_HIGH) {
            assert(width >= 7U && width <= 8U);
            ++high_count;
        } else {
            assert(horizontal.y0 == LABMATE_SCOPE_PLOT_Y_LOW);
            assert(width >= 11U && width <= 12U);
            ++low_count;
        }
    }
    assert(high_count == 6U && low_count == 6U);
}

static void empty_one_and_small_not_invented(void) {
    LabMateScopePlotLine lines[LABMATE_SCOPE_PLOT_MAX_LINES] = {0};
    LabMateScopeEdge edge[2] = {
        {.tick=100U,.high=true},
        {.tick=150U,.delta_ticks=50U,.high=false},
    };
    LabMateScopePlotStats s = labmate_scope_plot_focus(
        NULL, 0U, false, lines, LABMATE_SCOPE_PLOT_MAX_LINES);
    assert(s.result == LabMateScopePlotNoEdges && s.line_count == 0U);
    s = labmate_scope_plot_focus(edge, 1U, false, lines, LABMATE_SCOPE_PLOT_MAX_LINES);
    assert(s.result == LabMateScopePlotOneEdge && s.line_count == 0U);
    s = labmate_scope_plot_focus(edge, 2U, false, lines, LABMATE_SCOPE_PLOT_MAX_LINES);
    assert(s.result == LabMateScopePlotReady && s.line_count == 2U);
    assert(s.visible_edges == 2U && !s.cropped_old_edges);
    s = labmate_scope_plot_focus(NULL, 2U, false, lines, LABMATE_SCOPE_PLOT_MAX_LINES);
    assert(s.result == LabMateScopePlotInvalid && s.line_count == 0U);
    s = labmate_scope_plot_focus(edge, 65U, false, lines, LABMATE_SCOPE_PLOT_MAX_LINES);
    assert(s.result == LabMateScopePlotInvalid && s.line_count == 0U);
}
static void corrupt_last_interval_denied(void) {
    LabMateScopeEdge edges[15] = {0};
    LabMateScopePlotLine lines[LABMATE_SCOPE_PLOT_MAX_LINES] = {0};
    for(uint16_t i=0; i<15; ++i) {
        edges[i].tick = 100U + 100U * i;
        edges[i].delta_ticks = i ? 100U : 0U;
        edges[i].high = (i & 1U) == 0U;
    }
    edges[14].delta_ticks = 99U; /* mismatch between true timestamps */
    LabMateScopePlotStats s = labmate_scope_plot_focus(
        edges, 15U, false, lines, LABMATE_SCOPE_PLOT_MAX_LINES);
    assert(s.result == LabMateScopePlotTimebaseError && s.line_count == 0U);
}
int main(void) {
    focus_real_100_hz();
    focus_nonideal_1khz();
    empty_one_and_small_not_invented();
    corrupt_last_interval_denied();
    puts("v1.9 Logic Scope focused real-edge waveform viewport PASS");
    return 0;
}
