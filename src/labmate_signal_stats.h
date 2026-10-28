#pragma once
/* Bounded statistics across VERIFIED completed capture sessions.
 * Not a cycle-jitter estimate: source samples are session snapshots.
 * Read-only projection: no heap, GPIO, IRQ, SD, or HAL.
 */
#include "labmate_snapshot.h"
#define LABMATE_SIGNAL_STATS_MAX_SESSIONS 64U
typedef struct {
    uint32_t min_millihz;
    uint32_t max_millihz;
    uint64_t sum_millihz;
    uint64_t sum_sq_millihz; /* valid only while !sq_overflow */
    bool sq_overflow;
    uint8_t completed_sessions;
} LabMateSignalStatSlot;
typedef struct {
    LabMateSignalStatSlot source[2];
} LabMateSignalStats;
void labmate_signal_stats_init(LabMateSignalStats* stats);
bool labmate_signal_stats_record(LabMateSignalStats* stats, const LabMateSnapshotV1* snapshot);
bool labmate_signal_stats_read(
    const LabMateSignalStats* stats, uint8_t source,
    uint32_t* mean_millihz, uint32_t* min_millihz, uint32_t* max_millihz,
    uint8_t* completed_sessions);

/* Session-to-session spread of the sealed frequencies: population standard
 * deviation (mHz) and coefficient of variation (permille of the mean).
 * Needs >= 2 sealed sessions and an overflow-free exact 64-bit sum of squares;
 * otherwise returns false. Descriptive only: NOT cycle jitter or calibration. */
bool labmate_signal_stats_spread(
    const LabMateSignalStats* stats, uint8_t source,
    uint32_t* stddev_millihz, uint32_t* cv_permille);
