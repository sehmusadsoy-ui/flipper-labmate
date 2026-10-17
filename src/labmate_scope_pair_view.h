#pragma once
/* Read-only 128x64 Flipper Canvas page for SEQUENTIAL (not simultaneous)
 * comparison of two actually completed PC1 captures.
 */
#include <gui/gui.h>
#include "labmate_scope_pair.h"

bool labmate_scope_pair_view_draw(Canvas* canvas, const LabMateScopePair* pair,
                                  bool last_capture_valid);
