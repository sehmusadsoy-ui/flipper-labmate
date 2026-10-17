#include "labmate_navigation.h"
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

/* Historical persisted tool IDs must NEVER be reordered. */
_Static_assert(LabMateToolGpio == 0, "GPIO ID changed");
_Static_assert(LabMateToolFrequency == 1, "Frequency ID changed");
_Static_assert(LabMateToolPulse == 2, "Pulse ID changed");
_Static_assert(LabMateToolGenerator == 3, "PWM ID changed");
_Static_assert(LabMateToolLogger == 4, "Logger ID changed");
_Static_assert(LabMateToolHistory == 5, "History ID changed");
_Static_assert(LabMateToolAbout == 6, "About ID changed");
_Static_assert(LabMateToolProfiles == 7, "Profiles ID changed");
_Static_assert(LabMateToolCounter == 8, "Counter ID changed");
_Static_assert(LabMateToolButton == 9, "Button ID changed");
_Static_assert(LabMateToolAlerts == 10, "Alerts ID changed");
_Static_assert(LabMateToolUart == 11, "UART ID changed");
_Static_assert(LabMateToolOneWire == 12, "1-Wire ID changed");
_Static_assert(LabMateToolI2c == 13, "I2C ID changed");
_Static_assert(LabMateToolScope == 14, "Scope must be appended");
_Static_assert(LabMateGroupInfo == 4, "INFO must remain last");

int main(void) {
    const uint8_t sizes[] = {6, 2, 3, 3, 1};
    bool seen[LabMateToolCount] = {false};
    for(uint8_t group=0; group<LabMateGroupCount; ++group) {
        assert(labmate_nav_group_size(group) == sizes[group]);
        for(uint8_t i=0; i<sizes[group]; ++i) {
            uint8_t tool=labmate_nav_tool_at(group,i);
            assert(tool < LabMateToolCount && !seen[tool]);
            seen[tool] = true;
        }
        assert(labmate_nav_tool_at(group,sizes[group]) == LabMateToolInvalid);
    }
    for(uint8_t t=0; t<LabMateToolCount; ++t) assert(seen[t]);
    assert(labmate_nav_tool_at(LabMateGroupMeasure,5) == LabMateToolScope);
    assert(labmate_nav_tool_at(LabMateGroupInfo,0) == LabMateToolAbout);
    assert(labmate_nav_wrap(5,6,1) == 0);
    assert(labmate_nav_wrap(0,6,-1) == 5);
    assert(labmate_nav_first_visible(5,6,3) == 3);
    assert(labmate_nav_first_visible(0,6,3) == 0);
    assert(labmate_nav_group_size(255) == 0);
    puts("v1.9 Scope menu legacy IDs, navigation and final INFO PASS");
    return 0;
}
