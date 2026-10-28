#pragma once
/* LabMate Ultimate v2.0 Signal Doctor: measurement-grounded SYMPTOM analysis.
 *
 * Pure ISO C11. No heap, no HAL, no GPIO, no IRQ, no clock, no storage.
 * Input is ONLY a stopped, immutable copy of genuinely captured Logic Scope
 * edges (see labmate_scope_buffer.h) plus facts the capture driver measured.
 *
 * Rules identify SYMPTOMS in the captured edges. They never certify a board,
 * pin or component fault and never invent an edge, level or time. A short
 * capture, buffer overflow or unsafe clock yields INSUFFICIENT / UNSAFE.
 */
#include <stdbool.h>
#include <stdint.h>
#include "labmate_scope_buffer.h"

/* Why the native capture ended. Mirrors the Scope time guard terminal
 * results; UserStop covers OK/BACK while the capture was still running. */
typedef enum {
    LabMateSymptomEndUserStop = 0,
    LabMateSymptomEndNoTrigger,   /* no edge during the trigger window */
    LabMateSymptomEndQuiet,       /* edges seen, then none for the quiet window */
    LabMateSymptomEndFull,
    LabMateSymptomEndDurationLimit,
    LabMateSymptomEndSampleComplete,
} LabMateSymptomEndReason;

typedef enum {
    LabMateSymptomNone = 0,       /* no analysis for this capture */
    LabMateSymptomInsufficient,   /* too few real edges / window too short */
    LabMateSymptomUnsafe,         /* overflow, clock fault or invalid input */
    LabMateSymptomReady,          /* flags/counters below are valid */
} LabMateSymptomStatus;

#define LABMATE_SYMPTOM_STUCK_HIGH (1U << 0)
#define LABMATE_SYMPTOM_STUCK_LOW (1U << 1)
#define LABMATE_SYMPTOM_STOPPED_HIGH (1U << 2)
#define LABMATE_SYMPTOM_STOPPED_LOW (1U << 3)
#define LABMATE_SYMPTOM_MISSING_PULSE (1U << 4)
#define LABMATE_SYMPTOM_RUNT_PULSE (1U << 5)
#define LABMATE_SYMPTOM_PERIOD_SPREAD (1U << 6)

/* Tunable evidence thresholds. Defaults come from
 * labmate_doctor_symptom_defaults(); every value is visible on screen as
 * part of the evidence, never hidden. */
typedef struct {
    uint32_t stuck_min_window_ms;      /* zero-edge window needed for STUCK */
    uint16_t gap_ratio_permille;       /* interval >= this x median = gap (1750) */
    uint16_t runt_ratio_permille;      /* interval <= this x median = runt (250) */
    uint16_t spread_threshold_permille;/* (max-min)/mean period (100 = 10.0%) */
    uint16_t min_intervals_per_level;  /* real intervals needed per level (3) */
    uint16_t min_cycles_for_spread;    /* complete H-L-H cycles needed (4) */
} LabMateDoctorSymptomConfig;

typedef struct {
    const LabMateScopeEdge* edges; /* stopped, immutable capture copy */
    uint16_t count;
    uint32_t timebase_hz;          /* verified edge clock; 0 = unknown */
    bool initial_level;            /* level sampled when capture was armed */
    bool last_level;               /* level after the last edge (or initial) */
    uint32_t window_ms;            /* real capture window, START to END */
    LabMateSymptomEndReason end_reason;
    bool truncated;                /* overflow / dropped edges */
    bool clock_fault;              /* any clock/timebase uncertainty */
} LabMateDoctorSymptomInput;

typedef struct {
    LabMateSymptomStatus status;
    uint16_t flags;                /* LABMATE_SYMPTOM_* bit set */
    uint16_t edge_count;
    uint16_t complete_cycles;
    uint16_t gap_count;            /* intervals >= gap threshold */
    uint16_t runt_count;           /* intervals <= runt threshold */
    uint16_t high_intervals;
    uint16_t low_intervals;
    uint32_t median_high_ticks;
    uint32_t median_low_ticks;
    uint32_t worst_gap_permille;   /* worst interval / median, 0 if none */
    uint32_t spread_permille;      /* descriptive period spread; 0 if N/A */
    uint32_t window_ms;
    bool level_high;               /* stuck/stopped level when flagged */
} LabMateDoctorSymptomReport;

LabMateDoctorSymptomConfig labmate_doctor_symptom_defaults(void);

/* Returns false only for NULL arguments or an invalid configuration (the
 * report is then zeroed with status None). All other outcomes are reported
 * through report->status; INSUFFICIENT and UNSAFE never carry flags. */
bool labmate_doctor_symptoms_analyze(
    const LabMateDoctorSymptomInput* input,
    const LabMateDoctorSymptomConfig* config,
    LabMateDoctorSymptomReport* report);

typedef struct {
    char finding[24];
    char evidence[24];
    char next_check[24];
} LabMateDoctorSymptomText;

/* Three display lines of at most 20 printable ASCII characters each
 * (128x64 secondary font, x=4). Wording is advisory only. */
void labmate_doctor_symptom_text(
    const LabMateDoctorSymptomReport* report, LabMateDoctorSymptomText* text);
