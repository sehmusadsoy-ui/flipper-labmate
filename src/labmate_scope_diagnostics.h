#pragma once
/* Source-linked real-cycle timing diagnostics. Pure C11, no guessed edges.
 * Runs only on stopped/released E11 Scope captures, never in IRQ or redraw.
 * "gap_suspected" means observed approximately doubled PERIOD, not a
 * component fault or proof of a missing physical pulse.
 */
#include "labmate_scope_compare.h"
typedef struct {
    bool valid;
    uint16_t complete_cycles;
    uint32_t min_ticks;
    uint32_t max_ticks;
    uint32_t mean_ticks;
    uint32_t mean_abs_deviation_ticks;
    uint32_t spread_permille;
    bool gap_suspected;
} LabMateScopeDiagnostics;
bool labmate_scope_diagnostics_compute(
    const LabMateScopeEdge* edges, uint16_t count, uint32_t timebase_hz,
    LabMateScopeDiagnostics* out);
