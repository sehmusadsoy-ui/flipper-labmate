#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include "labmate_capture_live.h"

int main(void) {
    unsigned count = 0;
    for(unsigned bits = 0; bits < 64; ++bits) {
        const bool high = !!(bits & 1U);
        const bool hw = !!(bits & 2U);
        const bool irq = !!(bits & 4U);
        const bool owned = !!(bits & 8U);
        const bool blocked = !!(bits & 16U);
        const bool fault = !!(bits & 32U);
        const bool expected = (high ? hw && !irq : irq && !hw) &&
                              owned && !blocked && !fault;
        assert(labmate_frequency_ui_live(high,hw,irq,owned,blocked,fault)==expected);
        ++count;
    }
    for(unsigned bits = 0; bits < 16; ++bits) {
        const bool active = !!(bits & 1U);
        const bool owned = !!(bits & 2U);
        const bool blocked = !!(bits & 4U);
        const bool fault = !!(bits & 8U);
        assert(labmate_pulse_ui_live(active,owned,blocked,fault)==
               (active && owned && !blocked && !fault));
        ++count;
    }
    printf("E11 UI LIVE GUARDS HOST PASS: %u truth-table cases\n", count);
    return 0;
}
