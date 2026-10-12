#pragma once
#include <stdbool.h>
#include <stdint.h>

/* One configurable, visual-only measurement threshold; no HAL or SD access.
 * Values use user-facing units: frequency Hz, Pulse duty percent, Counter
 * rising-edge count, Button electrical settling milliseconds.
 */
typedef enum {
    LabMateAlertFrequency = 0,
    LabMateAlertPulseDuty,
    LabMateAlertCounter,
    LabMateAlertButtonSettle,
    LabMateAlertSourceCount
} LabMateAlertSource;

typedef struct {
    LabMateAlertSource source;
    uint32_t limit;
    bool armed;
    bool active; /* current valid sample >= limit */
    bool latched; /* last trip remains until DISARM/acknowledgment */
    bool has_sample;
    uint32_t trips;
} LabMateThreshold;

void labmate_threshold_init(LabMateThreshold* alert);
void labmate_threshold_change_source(LabMateThreshold* alert, int8_t direction);
void labmate_threshold_change_limit(LabMateThreshold* alert, int8_t direction);
void labmate_threshold_toggle(LabMateThreshold* alert);
void labmate_threshold_acknowledge(LabMateThreshold* alert);
void labmate_threshold_update(LabMateThreshold* alert, bool valid, uint64_t sample);
const char* labmate_threshold_source_name(LabMateAlertSource source);
const char* labmate_threshold_source_unit(LabMateAlertSource source);
