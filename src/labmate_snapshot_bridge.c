#include "labmate_snapshot_bridge.h"
#include <string.h>
#include <stdint.h>

/* Match the actual EXTI-safe Pulse pin list in labmate_capture_session.c:
 * PC0=0, PC1=1, PB2=3, PA4=5. Do not accept UI-only polling pins.
 */
bool labmate_snapshot_capture_pin_supported(uint8_t source, uint8_t pin_index) {
    if(source == LabMateSnapshotFrequency)
        return pin_index == 1U || pin_index == 4U;
    if(source == LabMateSnapshotPulse)
        return pin_index == 0U || pin_index == 1U ||
               pin_index == 3U || pin_index == 5U;
    return false;
}

static bool pulse_consistent(const LabMateCaptureEvidenceV1* e) {
    if(e->period_ticks == 0U || e->duty_permille > 1000U) return false;
    const uint64_t sum=(uint64_t)e->high_ticks+(uint64_t)e->low_ticks;
    if(sum!=(uint64_t)e->period_ticks) return false;
    /* The actual v1.9 period/duty calculation rounds to nearest permille. */
    const uint32_t rounded=(uint32_t)(((uint64_t)e->high_ticks*1000U+
                                   (uint64_t)e->period_ticks/2U)/e->period_ticks);
    return rounded==e->duty_permille;
}

bool labmate_snapshot_bridge_from_capture(
    const LabMateCaptureEvidenceV1* e, LabMateSnapshotV1* output) {
    if(!e || !output || e->source>LabMateSnapshotPulse ||
       e->pin_index>=LABMATE_SNAPSHOT_PIN_COUNT || e->capture_generation==0U ||
       e->observation_end_ms<e->observation_start_ms ||
       !labmate_snapshot_capture_pin_supported(e->source, e->pin_index)) return false;

    LabMateSnapshotV1 s;
    memset(&s,0,sizeof(s));
    s.schema_version=LABMATE_SNAPSHOT_VERSION;
    s.source=e->source;
    s.pin_index=e->pin_index;
    s.capture_generation=e->capture_generation;
    s.observation_start_ms=e->observation_start_ms;
    s.observation_end_ms=e->observation_end_ms;
    s.timebase_hz=e->timebase_hz;
    s.valid_sample_count=e->completed_sample_count;
    s.observed_edge_count=e->observed_edge_count;
    s.dropped_edge_count=e->dropped_edge_count;
    s.ownership_released=e->released;
    s.quality=LabMateSnapshotInsufficient;

    if(e->resource_busy || !e->released) {
        s.quality=LabMateSnapshotBusy;
    } else if(e->clock_unsafe || e->timebase_hz==0U) {
        s.quality=LabMateSnapshotClockUnsafe;
    } else if(e->overflow || e->dropped_edge_count!=0U) {
        s.quality=LabMateSnapshotOverflow;
    } else if(!e->measurement_valid || e->completed_sample_count==0U ||
              e->observed_edge_count<2U ||
              e->observation_start_ms==e->observation_end_ms) {
        s.quality=LabMateSnapshotInsufficient;
    } else if(e->source==LabMateSnapshotFrequency) {
        if(e->measured_frequency_millihz==0U) {
            s.quality=LabMateSnapshotInvalid;
        } else {
            s.frequency_millihz=e->measured_frequency_millihz;
            s.period_ticks=e->period_ticks; /* zero is legitimate for TIM2 path */
            s.quality=LabMateSnapshotValid;
        }
    } else if(!pulse_consistent(e)) {
        s.quality=LabMateSnapshotInvalid;
    } else {
        /* Deterministic integer conversion: timer Hz -> rounded millihertz. */
        const uint64_t numerator=(uint64_t)e->timebase_hz*1000ULL;
        const uint64_t mhz=(numerator+e->period_ticks/2U)/e->period_ticks;
        if(mhz==0U || mhz>UINT32_MAX) {
            s.quality=LabMateSnapshotOverflow;
        } else {
            s.frequency_millihz=(uint32_t)mhz;
            s.high_ticks=e->high_ticks;
            s.low_ticks=e->low_ticks;
            s.period_ticks=e->period_ticks;
            s.duty_permille=e->duty_permille;
            s.quality=LabMateSnapshotValid;
        }
    }
    if(s.quality==LabMateSnapshotValid &&
       !labmate_snapshot_v1_can_display_measurement(&s)) s.quality=LabMateSnapshotInvalid;
    /* Existing snapshot schema requires a nonzero-length interval when
     * samples exist. An incomplete reporter cannot forge a valid result. */
    if(!labmate_snapshot_v1_well_formed(&s)) return false;
    *output=s;
    return true;
}
