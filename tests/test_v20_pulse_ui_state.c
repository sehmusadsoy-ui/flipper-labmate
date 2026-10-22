#include "labmate_pulse_ui_state.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    unsigned accepted=0;
    for(unsigned mask=0;mask<16;mask++) {
        const bool irq=(mask&1U)!=0;
        const bool owner=(mask&2U)!=0;
        const bool blocked=(mask&4U)!=0;
        const bool release_fault=(mask&8U)!=0;
        const bool live=labmate_pulse_ui_live(irq,owner,blocked,release_fault);
        assert(live==(mask==3U));
        if(live) ++accepted;
    }
    assert(accepted==1U);
    puts("V20 PULSE RESUME UI POLICY PASS: 16 owner/IRQ/blocked/release cases");
    return 0;
}
