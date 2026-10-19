#include "labmate_scope_plot.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

static void check_empty_single(void) {
    LabMateScopePlotLine lines[4] = {0};
    LabMateScopePlotStats s = labmate_scope_plot_project(NULL, 0, false, lines, 4);
    assert(s.result == LabMateScopePlotNoEdges && s.line_count == 0);
    LabMateScopeEdge edge = {.tick = 123U, .high = true};
    s = labmate_scope_plot_project(&edge, 1U, false, lines, 4);
    assert(s.result == LabMateScopePlotOneEdge && s.line_count == 0 && s.window_cycles == 0);
    s = labmate_scope_plot_project(NULL, 1U, false, lines, 4);
    assert(s.result == LabMateScopePlotInvalid);
    s = labmate_scope_plot_project(&edge, 65U, false, lines, 4);
    assert(s.result == LabMateScopePlotInvalid);
}
static void check_real_duty(void) {
    /* Sample positions: +10 HIGH, +30 LOW, +70 HIGH => 20/40 duration.
     * Last HIGH interval has no observed falling edge and is not drawn. */
    LabMateScopeEdge edge[3] = {
        {.tick = 10U, .high = true},
        {.tick = 30U, .delta_ticks = 20U, .high = false},
        {.tick = 70U, .delta_ticks = 40U, .high = true},
    };
    LabMateScopePlotLine lines[4] = {0};
    LabMateScopePlotStats s = labmate_scope_plot_project(edge, 3U, true, lines, 4U);
    assert(s.result == LabMateScopePlotReady && s.line_count == 4U);
    assert(s.window_cycles == 60U && s.cropped_old_edges);
    assert(lines[0].x0 == 5U && lines[0].x1 == 44U);
    assert(lines[0].y0 == LABMATE_SCOPE_PLOT_Y_HIGH &&
           lines[0].y1 == LABMATE_SCOPE_PLOT_Y_HIGH);
    assert(lines[1].x0 == 44U &&
           lines[1].y0 == LABMATE_SCOPE_PLOT_Y_HIGH &&
           lines[1].y1 == LABMATE_SCOPE_PLOT_Y_LOW);
    assert(lines[2].x0 == 44U && lines[2].x1 == 122U);
    assert(lines[2].y0 == LABMATE_SCOPE_PLOT_Y_LOW &&
           lines[2].y1 == LABMATE_SCOPE_PLOT_Y_LOW);
    assert(lines[3].x0 == 122U &&
           lines[3].y0 == LABMATE_SCOPE_PLOT_Y_LOW &&
           lines[3].y1 == LABMATE_SCOPE_PLOT_Y_HIGH);
}
static void check_overflow_wrap_invalid(void) {
    LabMateScopeEdge wrap[] = {
        {.tick = UINT32_MAX - 9U, .high = true},
        {.tick = 15U, .delta_ticks = 25U, .high = false},
    };
    LabMateScopePlotLine lines[2];
    LabMateScopePlotStats s = labmate_scope_plot_project(wrap, 2, false, lines, 2);
    assert(s.result == LabMateScopePlotReady && s.window_cycles == 25);
    assert(lines[0].x1 == 122U);
    wrap[1].delta_ticks = 0;
    s = labmate_scope_plot_project(wrap, 2, false, lines, 2);
    assert(s.result == LabMateScopePlotTimebaseError && s.line_count == 0U);
    wrap[1].delta_ticks = 25U;
    wrap[1].high = true;
    s = labmate_scope_plot_project(wrap, 2, false, lines, 2);
    assert(s.result == LabMateScopePlotTimebaseError);
    wrap[1].high = false;
    s = labmate_scope_plot_project(wrap, 2, false, lines, 1);
    assert(s.result == LabMateScopePlotInvalid);
}
static void check_full_real_capture(void) {
    LabMateScopeEdge e[LABMATE_SCOPE_PLOT_MAX_EDGES];
    LabMateScopePlotLine line[LABMATE_SCOPE_PLOT_MAX_LINES];
    for(uint16_t i = 0; i < LABMATE_SCOPE_PLOT_MAX_EDGES; ++i) {
        e[i].tick = 100U + i;
        e[i].high = (i & 1U) == 0U;
        e[i].delta_ticks = i ? 1U : 0U;
    }
    LabMateScopePlotStats s = labmate_scope_plot_project(e, 64, true, line, 126);
    assert(s.result == LabMateScopePlotReady && s.line_count == 126U);
    assert(s.window_cycles == 63U && s.visible_edges == 64U);
    for(uint16_t i = 0; i < s.line_count; ++i) {
        assert(line[i].x0 >= 5U && line[i].x0 <= 122U);
        assert(line[i].x1 >= 5U && line[i].x1 <= 122U);
        assert(line[i].y0 == LABMATE_SCOPE_PLOT_Y_HIGH ||
               line[i].y0 == LABMATE_SCOPE_PLOT_Y_LOW);
        assert(line[i].y1 == LABMATE_SCOPE_PLOT_Y_HIGH ||
               line[i].y1 == LABMATE_SCOPE_PLOT_Y_LOW);
    }
    e[63].delta_ticks = LABMATE_SCOPE_MAX_SAFE_DELTA;
    s = labmate_scope_plot_project(e, 64, true, line, 126);
    assert(s.result == LabMateScopePlotTimebaseError && s.line_count == 0);
}
int main(void) {
    check_empty_single();
    check_real_duty();
    check_overflow_wrap_invalid();
    check_full_real_capture();
    puts("v1.9 Logic Scope true-edge 128x64 plotting host tests PASS");
    return 0;
}
