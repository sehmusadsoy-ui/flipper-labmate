#pragma once
/* LabMate v1.9 Signal Compare: sequential captures of ONE 3.3V digital
 * PC1 channel, not a simultaneous two-channel oscilloscope.
 * Pure ISO C, no GPIO/IRQ/UI/storage. Inputs are owned immutable copies.
 */
#include <stdbool.h>
#include <stdint.h>
#include "labmate_scope_buffer.h"

typedef enum {
    LabMateScopeMetricsReady = 0,
    LabMateScopeMetricsInsufficient,
    LabMateScopeMetricsInvalid,
    LabMateScopeMetricsClockInvalid,
} LabMateScopeMetricsStatus;

typedef struct {
    LabMateScopeMetricsStatus status;
    uint16_t completed_cycles;
    uint16_t edge_count;
    uint32_t timebase_hz;
    uint64_t frequency_millihz; /* rounded to nearest mHz */
    uint16_t duty_permille; /* rounded to nearest 0.1% */
    uint32_t min_period_ticks;
    uint32_t max_period_ticks;
    uint64_t total_high_ticks;
    uint64_t total_low_ticks;
} LabMateScopeMetrics;

typedef struct {
    bool comparable; /* Never a fabricated PASS/FAIL tolerance */
    int64_t frequency_delta_millihz; /* B minus A */
    int16_t duty_delta_permille; /* B minus A */
} LabMateScopeCompare;

/* A full cycle requires THREE actual consecutive edge levels H-L-H.
 * The first recorded edge can occur on either level; LOW-leading captures
 * skip that unmatched half cycle. No measurements are extrapolated outside
 * two physically observed bounding edges. Both captures may use distinct
 * CYCCNT timebases; each clock MUST be supplied as measured/verified Hz.
 * Caller must first stop capture, then copy edges in a critical section.
 */
LabMateScopeMetrics labmate_scope_metrics_from_edges(
    const LabMateScopeEdge* edges, uint16_t count, uint32_t timebase_hz);
LabMateScopeCompare labmate_scope_compare_metrics(
    const LabMateScopeMetrics* a, const LabMateScopeMetrics* b);
