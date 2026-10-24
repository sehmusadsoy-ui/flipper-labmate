/* Every possible release report, including all combinations of stale handles. */
#include "labmate_capture_release_gate.h"
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
int main(void) {
    unsigned accepted = 0U;
    assert(!labmate_capture_release_proven(NULL));
    for(uint32_t bits=0;bits<2048U;bits++) {
        LabMateCaptureReleaseEvidence e = {
            .scope_stop_confirmed = (bits & (1U << 0)) != 0,
            .frequency_low_active = (bits & (1U << 1)) != 0,
            .frequency_high_active = (bits & (1U << 2)) != 0,
            .pulse_active = (bits & (1U << 3)) != 0,
            .counter_active = (bits & (1U << 4)) != 0,
            .button_active = (bits & (1U << 5)) != 0,
            .frequency_low_lease_pending = (bits & (1U << 6)) != 0,
            .frequency_high_lease_pending = (bits & (1U << 7)) != 0,
            .pulse_lease_pending = (bits & (1U << 8)) != 0,
            .button_lease_pending = (bits & (1U << 9)) != 0,
            .release_fault = (bits & (1U << 10)) != 0,
        };
        const bool expected = bits == 1U;
        assert(labmate_capture_release_proven(&e) == expected);
        if(expected) accepted++;
    }
    assert(accepted == 1U);
    puts("Phase2K native-lease release gate PASS: 2048 reports, only 1 fully released");
    return 0;
}
