#pragma once
/* Flipper Zero 128x64 digital trace projection. Pure ISO C: no UI/GPIO/HAL.
 * Consume a CONSISTENT, IRQ-excluded, copied edge snapshot.
 * Show only intervals actually bounded by two observed edges. No signal
 * samples are fabricated before the first or after the last recorded edge.
 */
#include <stdbool.h>
#include <stdint.h>
#include "labmate_scope_buffer.h"

#define LABMATE_SCOPE_PLOT_MAX_EDGES 64U
/* Focus on the latest six digital periods instead of compressing 64
 * transitions into 117 LCD pixels. View-only: capture still stores 256. */
#define LABMATE_SCOPE_PLOT_FOCUS_EDGES 13U
#define LABMATE_SCOPE_PLOT_MAX_LINES (2U * (LABMATE_SCOPE_PLOT_MAX_EDGES - 1U))
#define LABMATE_SCOPE_PLOT_X_LEFT 5U
#define LABMATE_SCOPE_PLOT_X_RIGHT 122U
/* Keep trace strictly inside y=18..35; 128x64 LCD status glyphs are at
 * y=42..50 and must NEVER overlap the low-level trace. */
#define LABMATE_SCOPE_PLOT_Y_HIGH 20U
#define LABMATE_SCOPE_PLOT_Y_LOW 35U

typedef struct {
    uint8_t x0;
    uint8_t y0;
    uint8_t x1;
    uint8_t y1;
} LabMateScopePlotLine;

typedef enum {
    LabMateScopePlotReady = 0,
    LabMateScopePlotNoEdges,
    LabMateScopePlotOneEdge,
    LabMateScopePlotInvalid,
    LabMateScopePlotTimebaseError,
} LabMateScopePlotResult;

typedef struct {
    LabMateScopePlotResult result;
    uint16_t line_count;
    uint16_t visible_edges;
    bool cropped_old_edges; /* do not mistake displayed window for whole capture */
    uint32_t window_cycles;
} LabMateScopePlotStats;

/* `available` is the count of actually copied, sequential real edge events.
 * The source's full count may be higher; the caller should copy the most
 * recent <=64 edges from a consistent snapshot, and pass `cropped_old_edges`
 * from the full snapshot count (not fake a trigger at x=5).
 * Never pass an unsynchronised live IRQ-owned edge array here.
 */
LabMateScopePlotStats labmate_scope_plot_project(
    const LabMateScopeEdge* edges, uint16_t available, bool cropped_old_edges,
    LabMateScopePlotLine* out, uint16_t max_lines);

/* Choose only the last <=13 ACTUAL observed transitions from an IRQ-excluded
 * <=64-edge copy. Pure read-only viewport selection: original measurement and
 * 256-edge buffer stay untouched. Calls the same fail-closed projector. */
LabMateScopePlotStats labmate_scope_plot_focus(
    const LabMateScopeEdge* edges, uint16_t available, bool cropped_old_edges,
    LabMateScopePlotLine* out, uint16_t max_lines);
