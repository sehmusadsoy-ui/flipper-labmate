#include "labmate_signal_stats.h"
#include <string.h>
void labmate_signal_stats_init(LabMateSignalStats* stats) {
    if(stats) memset(stats, 0, sizeof(*stats));
}
bool labmate_signal_stats_record(LabMateSignalStats* stats, const LabMateSnapshotV1* snapshot) {
    if(!stats || !snapshot || snapshot->source > LabMateSnapshotPulse ||
       !labmate_snapshot_v1_can_display_measurement(snapshot)) return false;
    LabMateSignalStatSlot* s = &stats->source[snapshot->source];
    if(s->completed_sessions == LABMATE_SIGNAL_STATS_MAX_SESSIONS) return false;
    const uint32_t f = snapshot->frequency_millihz;
    if(!s->completed_sessions || f < s->min_millihz) s->min_millihz = f;
    if(!s->completed_sessions || f > s->max_millihz) s->max_millihz = f;
    s->sum_millihz += f;
    uint64_t sq;
    if(s->sq_overflow || __builtin_mul_overflow((uint64_t)f, (uint64_t)f, &sq) ||
       __builtin_add_overflow(s->sum_sq_millihz, sq, &s->sum_sq_millihz))
        s->sq_overflow = true;
    ++s->completed_sessions;
    return true;
}
bool labmate_signal_stats_read(
    const LabMateSignalStats* stats, uint8_t source, uint32_t* mean,
    uint32_t* min, uint32_t* max, uint8_t* count) {
    if(!stats || source > LabMateSnapshotPulse || !mean || !min || !max || !count)
        return false;
    const LabMateSignalStatSlot* s = &stats->source[source];
    if(!s->completed_sessions) return false;
    const uint64_t average = (s->sum_millihz + s->completed_sessions / 2U) /
        s->completed_sessions;
    if(average > UINT32_MAX) return false;
    *mean = (uint32_t)average;
    *min = s->min_millihz;
    *max = s->max_millihz;
    *count = s->completed_sessions;
    return true;
}

static uint64_t isqrt_u64(uint64_t v) {
    uint64_t lo = 0U, hi = v < 0xFFFFFFFFULL ? v : 0xFFFFFFFFULL;
    while(lo < hi) {
        const uint64_t mid = lo + (hi - lo + 1U) / 2U;
        if(mid <= v / mid) lo = mid; else hi = mid - 1U;
    }
    return lo;
}

bool labmate_signal_stats_spread(
    const LabMateSignalStats* stats, uint8_t source,
    uint32_t* stddev_millihz, uint32_t* cv_permille) {
    if(!stats || source > LabMateSnapshotPulse || !stddev_millihz || !cv_permille)
        return false;
    const LabMateSignalStatSlot* s = &stats->source[source];
    const uint64_t n = s->completed_sessions;
    if(n < 2U || s->sq_overflow || !s->sum_millihz) return false;
    uint64_t n_sumsq, sum_sq_of_sum, numerator;
    if(__builtin_mul_overflow(n, s->sum_sq_millihz, &n_sumsq) ||
       __builtin_mul_overflow(s->sum_millihz, s->sum_millihz, &sum_sq_of_sum) ||
       n_sumsq < sum_sq_of_sum) return false;
    numerator = n_sumsq - sum_sq_of_sum;
    const uint64_t variance = numerator / (n * n);
    const uint64_t sd = isqrt_u64(variance);
    const uint64_t mean = (s->sum_millihz + n / 2U) / n;
    if(!mean || sd > UINT32_MAX) return false;
    const uint64_t cv = (sd * 1000U + mean / 2U) / mean;
    if(cv > UINT32_MAX) return false;
    *stddev_millihz = (uint32_t)sd;
    *cv_permille = (uint32_t)cv;
    return true;
}
