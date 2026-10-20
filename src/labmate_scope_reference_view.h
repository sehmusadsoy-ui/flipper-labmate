#pragma once
/* Render one actual completed PC1 measurement against a named reference.
 * Read-only presentation: no capture, file I/O, IRQ or GPIO changes.
 */
#include <gui/gui.h>
#include "labmate_scope_tolerance.h"

bool labmate_scope_reference_view_draw(
    Canvas* canvas,
    LabMateScopeReferencePreset selected,
    LabMateScopeToleranceResult result,
    const LabMateScopeMetrics* measured);
