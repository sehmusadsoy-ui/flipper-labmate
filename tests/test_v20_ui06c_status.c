/* Pure host contract: match the original GPIO status priority exactly. */
#include "labmate_ui_status.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    unsigned cases = 0;
    for(unsigned f = 0; f < 2; ++f)
    for(unsigned b = 0; b < 2; ++b)
    for(unsigned h = 0; h < 2; ++h) {
        const char* expected = f ? "ERR" : b ? "BUSY" : h ? "HOLD" : "LIVE";
        const LabMateUiStatus status = labmate_ui_gpio_monitor_status(f!=0, b!=0, h!=0);
        const char* label = labmate_ui_status_label(status);
        assert(!strcmp(label, expected));
        assert(strlen(label) <= 4U);
        /* GPIO's original right badge is x=91, width=35. */
        assert(91U + 4U + strlen(label)*6U <= 91U + 35U);
        ++cases;
    }
    assert(!strcmp(labmate_ui_status_label((LabMateUiStatus)-1), "ERR"));
    assert(!strcmp(labmate_ui_status_label((LabMateUiStatus)255), "ERR"));
    printf("UI-06C GPIO pure status contract PASS: %u states + 2 invalid status values\n",cases);
    return cases==8U?0:1;
}
