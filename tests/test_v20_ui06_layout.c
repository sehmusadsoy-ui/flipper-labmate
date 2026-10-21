#include "labmate_ui_layout.h"
#define HOST_SECONDARY_ADVANCE 6
#include <assert.h>
#include <stdio.h>
/* This test is geometry-only, not physical font raster certification. */
_Static_assert(LABMATE_UI_WIDTH==128 && LABMATE_UI_HEIGHT==64, "Flipper LCD dimensions");
_Static_assert(LABMATE_UI_HEADER_TITLE_X>=0, "Title x bound");
_Static_assert(LABMATE_UI_HEADER_BASELINE_Y<LABMATE_UI_HEADER_RULE_Y, "Header title precedes rule");
_Static_assert(LABMATE_UI_HEADER_RULE_Y<LABMATE_UI_FOOTER_RULE_Y, "Content region nonempty");
_Static_assert(LABMATE_UI_FOOTER_RULE_Y<LABMATE_UI_FOOTER_BASELINE_Y, "Footer below rule");
_Static_assert(LABMATE_UI_FOOTER_BASELINE_Y<LABMATE_UI_HEIGHT, "Footer inside LCD");
_Static_assert(LABMATE_UI_FOOTER_TRIPLE_LEFT_X + HOST_SECONDARY_ADVANCE * LABMATE_UI_FOOTER_TRIPLE_LEFT_MAX_CHARS < LABMATE_UI_FOOTER_TRIPLE_CENTER_X, "Triple left and center separated");
_Static_assert(LABMATE_UI_FOOTER_TRIPLE_CENTER_X + HOST_SECONDARY_ADVANCE * LABMATE_UI_FOOTER_TRIPLE_CENTER_MAX_CHARS < LABMATE_UI_FOOTER_TRIPLE_RIGHT_X, "Triple center and right separated");
_Static_assert(LABMATE_UI_FOOTER_TRIPLE_RIGHT_X + HOST_SECONDARY_ADVANCE * LABMATE_UI_FOOTER_TRIPLE_RIGHT_MAX_CHARS <= LABMATE_UI_WIDTH, "Triple right inside 128 pixels");
_Static_assert(LABMATE_UI_FOOTER_PAIR_LEFT_X + 10*HOST_SECONDARY_ADVANCE < LABMATE_UI_FOOTER_PAIR_RIGHT_X, "Pair columns separated");
_Static_assert(LABMATE_UI_FOOTER_PAIR_RIGHT_X + 10*HOST_SECONDARY_ADVANCE <= LABMATE_UI_WIDTH, "Pair inside 128 pixels");
int main(void) { puts("UI-06 static layout 128x64 pair/triple contract PASS");return 0; }
