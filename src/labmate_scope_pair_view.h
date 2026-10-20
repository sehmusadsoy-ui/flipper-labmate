#pragma once
/* Read-only 128x64 Flipper Canvas page for SEQUENTIAL (not simultaneous)
 * comparison of two actually completed PC1 captures.
 */
#include <gui/gui.h>
#include "labmate_scope_pair.h"

/* page 0 = A/B frequency/duty and B-A deltas; page 1=A timing, page 2=B timing. */
bool labmate_scope_pair_view_draw(Canvas* canvas, const LabMateScopePair* pair,
                                  bool last_capture_valid, uint8_t page);
