#pragma once

#include "labmate_scope_trace.h"

/* v1.9 L1 pure preview: map observed digital transitions to exactly
 * 120 horizontal pixel columns for a future 128x64 canvas. This is NOT
 * a GPIO sampler or real on-device renderer. No tick rate is known.
 * Reserve remaining pixels for margins/status; Y levels are UI-owned.
 */
#define LABMATE_SCOPE_GRAPH_COLUMNS 120U

typedef enum {
    LabMateScopeViewInvalid = 0,
    LabMateScopeViewWaitingTrigger,
    LabMateScopeViewNotTriggered,
    LabMateScopeViewNoSpan,
    LabMateScopeViewTrace,
    LabMateScopeViewOverflow,
    LabMateScopeViewFault,
} LabMateScopeViewState;

typedef struct {
    /* Level entering/leaving the pixel bucket (not a sampled average).
     * transitions >= 2 means this pixel hides multiple transitions; it
     * MUST display a density mark, never a fake clean pulse waveform.
     * The first trace event at t=0 is a level anchor, not an edge.
     */
    uint8_t entering_level;
    uint8_t leaving_level;
    uint8_t transitions;
} LabMateScopePixelColumn;

typedef struct {
    LabMateScopePixelColumn columns[LABMATE_SCOPE_GRAPH_COLUMNS];
    uint32_t window_start_ticks;
    uint32_t window_end_ticks;
    uint16_t dense_columns;
    LabMateScopeViewState state;
    bool has_waveform;
    bool left_cropped;
    bool right_cropped;
} LabMateScopeProjection;

/* Return false for null input, invalid range or a request past LAST
 * OBSERVED time. On false, output (if nonnull) is cleared and state
 * is Invalid. Output is deterministic, bounded and caller-owned.
 *
 * Armed traces without a trigger and stopped untriggered traces
 * return true with their explicit no-waveform statuses. If no time
 * progression exists, NoSpan never invents a horizontal duration.
 *
 * After OVERFLOW the last reliable tick is the LAST STORED event;
 * the omitted transition and subsequent level are unknown.
 * Requests beyond that tick fail, rather than drawing an invented
 * stable level. View state still reports Overflow for valid ranges.
 *
 * Caller must supply a synchronized immutable copy of the trace;
 * never use directly from GPIO ISR / concurrent writer.
 */
bool labmate_scope_project(
    const LabMateScopeTrace* trace,
    uint32_t window_start_ticks,
    uint32_t window_end_ticks,
    LabMateScopeProjection* output);
