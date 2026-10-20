#pragma once
/* View-only Flipper Zero Canvas renderer. Caller supplies coherent host/IRQ-
 * excluded geometry: no GPIO, IRQ, storage or acquisition in the render path.
 */
#include <gui/gui.h>
#include "labmate_scope_plot.h"
#include "labmate_scope_compare.h"

typedef enum {
    LabMateScopeDisplayArmed = 0,
    LabMateScopeDisplayRunning,
    LabMateScopeDisplayStopped,
    LabMateScopeDisplayNoTrigger,
    LabMateScopeDisplayQuiet,
    LabMateScopeDisplayFull,
    LabMateScopeDisplayBusy,
    LabMateScopeDisplayUnsupported,
    LabMateScopeDisplayError,
} LabMateScopeDisplayState;

typedef struct {
    const LabMateScopePlotLine* lines; /* caller owns for duration of draw */
    LabMateScopePlotStats plot;
    LabMateScopeDisplayState state;
    uint16_t total_edges; /* consistent IRQ-excluded snapshot count */
    const LabMateScopeMetrics* completed; /* optional verified STOP-only data; never live */
} LabMateScopeDisplay;

/* Return false rather than drawing any unchecked/out-of-bounds traces. */
bool labmate_scope_display_draw(Canvas* canvas, const LabMateScopeDisplay* display);
