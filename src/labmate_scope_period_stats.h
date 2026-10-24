#pragma once
/* Real captured Scope timing spread, not calibrated jitter or stability diagnosis.
 * Uses ONLY genuine complete cycles; no synthetic or interpolated edge.
 */
#include "labmate_scope_compare.h"
typedef struct {
    uint32_t mean_period_ticks;
    uint32_t min_period_ticks;
    uint32_t max_period_ticks;
    uint32_t spread_permille; /* (max-min)/mean, rounded to 0.1%; descriptive ONLY */
    uint16_t completed_cycles;
} LabMateScopePeriodStats;
bool labmate_scope_period_stats(
    const LabMateScopeMetrics* metrics, LabMateScopePeriodStats* result);
