#include "labmate_frequency_ui_state.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    unsigned valid=0;
    for(unsigned v=0;v<64;v++) {
        const bool high=(v&1U)!=0, high_active=(v&2U)!=0;
        const bool low_active=(v&4U)!=0, owner=(v&8U)!=0;
        const bool blocked=(v&16U)!=0, fault=(v&32U)!=0;
        const bool live=labmate_frequency_ui_live(
            high,high_active,low_active,owner,blocked,fault);
        assert(live==(owner&&!blocked&&!fault&&
               (high ? (high_active&&!low_active) : (low_active&&!high_active))));
        if(live)++valid;
    }
    assert(valid==2U);
    puts("V20 FREQ E11 LIVE POLICY PASS: 64 combinations; 2 valid");
    return 0;
}
