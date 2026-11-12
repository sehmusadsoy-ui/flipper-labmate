#include "labmate_threshold.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    LabMateThreshold a;
    labmate_threshold_init(&a);
    assert(a.source == LabMateAlertFrequency && a.limit == 100U && !a.armed);
    labmate_threshold_update(&a, true, 1000U);
    assert(!a.latched && a.trips == 0U); /* disarmed */
    labmate_threshold_change_limit(&a, -1);
    assert(a.limit == 90U);
    labmate_threshold_toggle(&a);
    assert(a.armed && !a.latched);
    labmate_threshold_change_limit(&a, 1);
    labmate_threshold_change_source(&a, 1);
    assert(a.source == LabMateAlertFrequency && a.limit == 90U); /* locked */
    labmate_threshold_update(&a, false, UINT64_MAX);
    assert(!a.latched && !a.has_sample);
    labmate_threshold_update(&a, true, 89U);
    assert(!a.active && a.trips == 0U);
    labmate_threshold_update(&a, true, 90U);
    assert(a.active && a.latched && a.trips == 1U);
    labmate_threshold_update(&a, true, 500U);
    assert(a.trips == 1U);
    labmate_threshold_acknowledge(&a);
    assert(!a.latched && a.active);
    labmate_threshold_update(&a, true, 200U);
    assert(!a.latched && a.trips == 1U); /* no repeat while above */
    labmate_threshold_update(&a, true, 80U);
    assert(!a.active && !a.latched);
    labmate_threshold_update(&a, true, 91U);
    assert(a.trips == 2U && a.latched);
    labmate_threshold_update(&a, false, UINT64_MAX);
    assert(!a.active && a.latched); /* retain until ack */
    labmate_threshold_toggle(&a);
    assert(!a.armed && !a.latched && a.trips == 0U);
    labmate_threshold_change_source(&a, -1);
    assert(a.source == LabMateAlertButtonSettle && a.limit == 20U);
    assert(strcmp(labmate_threshold_source_unit(a.source), "ms") == 0);
    for(int i = 0; i < 1000; ++i) labmate_threshold_change_limit(&a, 1);
    assert(a.limit == 1000U);
    for(int i = 0; i < 1000; ++i) labmate_threshold_change_limit(&a, -1);
    assert(a.limit == 1U);
    labmate_threshold_change_source(&a, 1);
    assert(a.source == LabMateAlertFrequency && a.limit == 100U);
    labmate_threshold_change_source(&a, 1);
    assert(a.source == LabMateAlertPulseDuty && a.limit == 50U);
    labmate_threshold_toggle(&a);
    labmate_threshold_update(&a, true, 49U);
    assert(!a.latched);
    labmate_threshold_update(&a, true, 50U);
    assert(a.latched && a.trips == 1U);
    labmate_threshold_toggle(&a);
    labmate_threshold_change_source(&a, 1);
    assert(a.source == LabMateAlertCounter && a.limit == 100U);
    labmate_threshold_toggle(&a);
    labmate_threshold_update(&a, true, UINT64_MAX);
    assert(a.trips == 1U && a.latched);
    labmate_threshold_toggle(&a);
    assert(labmate_threshold_source_name(LabMateAlertSourceCount)[0] == '\0');
    /* Hold-to-repeat acceleration: scaled steps clamp and never wrap. */
    labmate_threshold_init(&a);
    labmate_threshold_change_limit_scaled(&a, 1, 0U); /* 0 behaves as 1x */
    assert(a.limit == 110U);
    labmate_threshold_change_limit_scaled(&a, 1, 100U);
    assert(a.limit == 1110U);
    labmate_threshold_change_limit_scaled(&a, 1, UINT32_MAX);
    assert(a.limit == 50000U);
    labmate_threshold_change_limit_scaled(&a, -1, 1000U);
    assert(a.limit == 40000U);
    labmate_threshold_change_limit_scaled(&a, -1, UINT32_MAX);
    assert(a.limit == 1U);
    labmate_threshold_toggle(&a); /* armed limits stay locked */
    labmate_threshold_change_limit_scaled(&a, 1, 1000U);
    assert(a.limit == 1U);
    labmate_threshold_toggle(&a);
    puts("Threshold Alerts portable tests PASS");
    return 0;
}
