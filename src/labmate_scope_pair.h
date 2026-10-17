#pragma once
/* LabMate v1.9 Signal Compare A/B: two SEQUENTIAL PC1 captures, never dual
 * channel or simultaneous edges. Pure ISO C (no HAL, GUI, GPIO or storage).
 */
#include "labmate_scope_compare.h"

typedef enum {
    LabMateScopePairNone = 0,
    LabMateScopePairNeedCapture,
    LabMateScopePairInvalidSample,
    LabMateScopePairNeedA,
    LabMateScopePairNeedFreshB,
    LabMateScopePairSavedA,
    LabMateScopePairSavedB,
} LabMateScopePairNotice;

typedef struct {
    LabMateScopeMetrics a;
    LabMateScopeMetrics b;
    LabMateScopeCompare delta;
    uint32_t generation_a;
    uint32_t generation_b;
    bool has_a;
    bool has_b;
    LabMateScopePairNotice notice;
} LabMateScopePair;

void labmate_scope_pair_reset(LabMateScopePair* pair);

/* Called ONLY after completed STOP + owned IRQ teardown and validation of
 * physical clock and copied/immutable edges. Generation is a monotonically
 * increasing app-owned capture number (0 is invalid). B requires a NEW run.
 * Saving a new A deliberately invalidates previously saved B/delta.
 */
bool labmate_scope_pair_save_a(
    LabMateScopePair* pair, const LabMateScopeMetrics* measured,
    uint32_t generation);
bool labmate_scope_pair_save_b(
    LabMateScopePair* pair, const LabMateScopeMetrics* measured,
    uint32_t generation);
