/* Portable navigation tests: exhaustive access to all 7 existing tools.
 * Do not include this host test in the firmware FAP build.
 */
#include "labmate_navigation.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>

int main(void) {
    const uint8_t expected_sizes[] = {3U, 1U, 2U, 1U};
    const uint8_t expected_tools[][LABMATE_NAV_MAX_CHILDREN] = {
        {LabMateToolGpio, LabMateToolFrequency, LabMateToolPulse},
        {LabMateToolGenerator, LabMateToolInvalid, LabMateToolInvalid},
        {LabMateToolLogger, LabMateToolHistory, LabMateToolInvalid},
        {LabMateToolAbout, LabMateToolInvalid, LabMateToolInvalid},
    };
    uint8_t visits[LabMateToolCount] = {0};
    for(uint8_t group = 0U; group < LabMateGroupCount; ++group) {
        assert(labmate_nav_group_size(group) == expected_sizes[group]);
        assert(labmate_nav_group_icon(group) == expected_tools[group][0]);
        assert(strlen(labmate_nav_group_title(group)) > 0U);
        for(uint8_t i = 0U; i < LABMATE_NAV_MAX_CHILDREN; ++i) {
            const uint8_t tool = labmate_nav_tool_at(group, i);
            if(i >= expected_sizes[group]) {
                assert(tool == LabMateToolInvalid);
                continue;
            }
            assert(tool == expected_tools[group][i]);
            assert(tool < LabMateToolCount);
            assert(strlen(labmate_nav_tool_title(tool)) > 0U);
            ++visits[tool];
        }
        assert(labmate_nav_wrap(0U, expected_sizes[group], -1) ==
               (uint8_t)(expected_sizes[group] - 1U));
        assert(labmate_nav_wrap(expected_sizes[group] - 1U, expected_sizes[group], 1) == 0U);
        assert(labmate_nav_wrap(0U, expected_sizes[group], 0) == 0U);
    }
    for(uint8_t tool = 0; tool < LabMateToolCount; ++tool) assert(visits[tool] == 1U);
    assert(labmate_nav_first_visible(2U, 3U, 3U) == 0U);
    assert(labmate_nav_first_visible(1U, 2U, 3U) == 0U);
    assert(labmate_nav_first_visible(3U, 4U, 3U) == 1U);
    assert(labmate_nav_first_visible(0U, 4U, 3U) == 0U);
    assert(labmate_nav_first_visible(255U, 0U, 3U) == 0U);
    assert(labmate_nav_first_visible(2U, 5U, 0U) == 0U);
    assert(labmate_nav_group_size(255U) == 0U);
    assert(labmate_nav_tool_at(255U, 0U) == LabMateToolInvalid);
    assert(labmate_nav_tool_at(0U, 3U) == LabMateToolInvalid);
    assert(labmate_nav_tool_title(255U)[0] == '\0');
    assert(labmate_nav_group_title(255U)[0] == '\0');
    assert(labmate_nav_wrap(200U, 0U, 1) == 0U);
    assert(labmate_nav_wrap(255U, 3U, 1) == 1U);
    assert(labmate_nav_wrap(255U, 3U, -1) == 2U);
    puts("LabMate v1.6 navigation mapping/wrap: all 7 tools reachable once");
    return 0;
}
