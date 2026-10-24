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
