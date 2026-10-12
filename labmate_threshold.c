#include "labmate_threshold.h"
#include <limits.h>

/* Conservative limits. No dynamic memory, file writes or pin acquisition. */
static const uint32_t initial_limits[LabMateAlertSourceCount] = {100U, 50U, 100U, 20U};
static const uint32_t min_limits[LabMateAlertSourceCount] = {1U, 5U, 1U, 1U};
static const uint32_t max_limits[LabMateAlertSourceCount] = {50000U, 95U, 1000000U, 1000U};
static const uint32_t limit_steps[LabMateAlertSourceCount] = {10U, 5U, 10U, 5U};
static const char* const names[LabMateAlertSourceCount] = {
    "FREQUENCY", "PULSE DUTY", "EDGE COUNT", "BUTTON SETTLE"
};
static const char* const units[LabMateAlertSourceCount] = {
    "Hz", "%", "edges", "ms"
};

void labmate_threshold_init(LabMateThreshold* a) {
    *a = (LabMateThreshold){0};
    a->source = LabMateAlertFrequency;
    a->limit = initial_limits[LabMateAlertFrequency];
}

void labmate_threshold_change_source(LabMateThreshold* a, int8_t direction) {
    if(a->armed || direction == 0) return;
    if(direction > 0) {
        a->source = (LabMateAlertSource)((a->source + 1U) % LabMateAlertSourceCount);
    } else {
        a->source = (LabMateAlertSource)(
            (a->source + LabMateAlertSourceCount - 1U) % LabMateAlertSourceCount);
    }
    a->limit = initial_limits[a->source];
    a->active = false;
    a->latched = false;
    a->has_sample = false;
    a->trips = 0U;
}

void labmate_threshold_change_limit(LabMateThreshold* a, int8_t direction) {
    if(a->armed || direction == 0) return;
    const uint32_t min = min_limits[a->source];
    const uint32_t max = max_limits[a->source];
    const uint32_t step = limit_steps[a->source];
    if(direction > 0) {
        a->limit = a->limit >= max - step ? max : a->limit + step;
    } else {
        a->limit = a->limit <= min + step ? min : a->limit - step;
    }
    a->active = false;
    a->latched = false;
    a->has_sample = false;
    a->trips = 0U;
}

void labmate_threshold_toggle(LabMateThreshold* a) {
    a->armed = !a->armed;
    a->active = false;
    a->latched = false;
    a->has_sample = false;
    a->trips = 0U;
}

void labmate_threshold_acknowledge(LabMateThreshold* a) {
    a->latched = false;
}

void labmate_threshold_update(LabMateThreshold* a, bool valid, uint64_t sample) {
    if(!a->armed) return;
    if(!valid) {
        a->active = false;
        a->has_sample = false;
        return; /* Missing/held/stopped sample is never an alarm trigger. */
    }
    const bool now_above = sample >= a->limit;
    if(now_above && (!a->has_sample || !a->active)) {
        if(a->trips < UINT32_MAX) ++a->trips;
        a->latched = true;
    }
    a->active = now_above;
    a->has_sample = true;
}

const char* labmate_threshold_source_name(LabMateAlertSource source) {
    return source < LabMateAlertSourceCount ? names[source] : "";
}

const char* labmate_threshold_source_unit(LabMateAlertSource source) {
    return source < LabMateAlertSourceCount ? units[source] : "";
}
