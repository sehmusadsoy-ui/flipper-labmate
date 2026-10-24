#include "labmate_level_witness.h"
#include <string.h>
#include <stdint.h>
static uint32_t milliseconds(uint32_t tick,uint32_t hz) {
    if(!hz) return 0U;
    const uint64_t val=(uint64_t)tick*1000U/hz;
    return !val || val>UINT32_MAX ? 0U : (uint32_t)val;
}
void labmate_level_invalidate(LabMateLevelWitness* w) {
    if(w){w->valid=false;w->active=false;w->sealed=false;}
}
bool labmate_level_begin(LabMateLevelWitness* w,uint8_t pin,bool level,
                         uint32_t tick,uint32_t hz) {
    if(!w) return false;
    memset(w,0,sizeof(*w));
    const uint32_t now=milliseconds(tick,hz);
    if(pin>=8U||!now||!hz) return false;
    *w=(LabMateLevelWitness){
        .pin=pin,.samples=1,.tick_hz=hz,.start_ms=now,
        .last_ms=now,.level=level,.valid=true,.active=true
    };
    return true;
}
bool labmate_level_observe(LabMateLevelWitness* w,uint8_t pin,bool level,
                           uint32_t tick,uint32_t hz) {
    if(!w||!w->valid||!w->active||w->sealed||w->pin!=pin||hz!=w->tick_hz) {
        labmate_level_invalidate(w);return false;
    }
    const uint32_t now=milliseconds(tick,hz);
    if(!now||now<=w->last_ms||now-w->last_ms>LABMATE_LEVEL_MAX_GAP_MS||
       w->samples==UINT16_MAX) {
        labmate_level_invalidate(w);return false;
    }
    if(level!=w->level) {
        if(w->transitions==UINT16_MAX){
            labmate_level_invalidate(w);return false;
        }
        ++w->transitions;
    }
    w->level=level;
    w->last_ms=now;
    ++w->samples;
    return true;
}
void labmate_level_finish(LabMateLevelWitness* w,uint8_t pin,bool released,
                          uint32_t tick,uint32_t hz) {
    if(!w||!w->active||!w->valid||w->pin!=pin||!released||
       hz!=w->tick_hz) {
        labmate_level_invalidate(w);return;
    }
    const uint32_t now=milliseconds(tick,hz);
    if(!now||now<w->last_ms||now-w->last_ms>LABMATE_LEVEL_MAX_GAP_MS) {
        labmate_level_invalidate(w);return;
    }
    w->active=false;
    w->sealed=true;
}
LabMateLevelFinding labmate_level_assess(
    const LabMateLevelWitness* w,uint32_t duration_ms) {
    if(!w||!duration_ms||!w->valid||!w->sealed||w->active||
       w->samples<10U||w->last_ms<=w->start_ms||
       w->last_ms-w->start_ms<duration_ms) return LabMateLevelNoEvidence;
    if(w->transitions>0U) return LabMateLevelTransitions;
    return w->level?LabMateLevelSampledHigh:LabMateLevelSampledLow;
}
