/* Portable navigation tests: exhaustive access to all 15 tools (including v1.9 Scope).
 * Do not include this host test in the firmware FAP build.
 */
#include "labmate_navigation.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>

int main(void) {
    _Static_assert(LabMateToolScope == 14, "historical tool IDs must not shift");
    _Static_assert(LabMateToolCount == 17, "v2.0 appended tool count");
    _Static_assert(LabMateGroupInfo == LabMateGroupCount - 1, "INFO must remain last");
    const uint8_t expected_sizes[] = {7U, 2U, 4U, 3U, 1U};
    const uint8_t expected_tools[][LABMATE_NAV_MAX_CHILDREN] = {
        {LabMateToolGpio, LabMateToolFrequency, LabMateToolPulse, LabMateToolCounter, LabMateToolButton, LabMateToolScope, LabMateToolDoctor},
        {LabMateToolGenerator, LabMateToolAlerts, LabMateToolInvalid, LabMateToolInvalid, LabMateToolInvalid, LabMateToolInvalid, LabMateToolInvalid},
        {LabMateToolLogger, LabMateToolHistory, LabMateToolProfiles, LabMateToolDashboard, LabMateToolInvalid, LabMateToolInvalid, LabMateToolInvalid},
        {LabMateToolUart, LabMateToolI2c, LabMateToolOneWire, LabMateToolInvalid, LabMateToolInvalid, LabMateToolInvalid, LabMateToolInvalid},
        {LabMateToolAbout, LabMateToolInvalid, LabMateToolInvalid, LabMateToolInvalid, LabMateToolInvalid, LabMateToolInvalid, LabMateToolInvalid},
    };
    /* Stable ROOT ID order: COMM above SETTINGS; About remains last.
     * Tool IDs stay stable for Profiles; only root group positions change. */
    assert(LabMateGroupMeasure == 0);
    assert(LabMateGroupOutput == 1);
    assert(LabMateGroupRecords == 2);
    assert(LabMateGroupComm == 3);
    assert(LabMateGroupInfo == 4);
    assert(LabMateGroupInfo == LabMateGroupCount - 1);
    assert(strcmp(labmate_nav_group_title(LabMateGroupInfo), "SETTINGS") == 0);
    assert(strcmp(labmate_nav_group_title(LabMateGroupComm), "COMM") == 0);
    assert(labmate_nav_tool_at(LabMateGroupInfo, 0U) == LabMateToolAbout);
    assert(labmate_nav_tool_at(LabMateGroupComm, 0U) == LabMateToolUart);
    assert(labmate_nav_tool_at(LabMateGroupComm, 1U) == LabMateToolI2c);
    assert(labmate_nav_tool_at(LabMateGroupComm, 2U) == LabMateToolOneWire);
    assert(LabMateToolOneWire == LabMateToolUart + 1);
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
    assert(labmate_nav_tool_at(0U, 3U) == LabMateToolCounter);
    assert(labmate_nav_tool_at(0U, 4U) == LabMateToolButton);
    assert(labmate_nav_tool_at(0U, 5U) == LabMateToolScope);
    assert(labmate_nav_tool_at(0U, 6U) == LabMateToolDoctor);
    assert(labmate_nav_tool_at(0U, 7U) == LabMateToolInvalid);
    assert(labmate_nav_tool_at(1U, 1U) == LabMateToolAlerts);
    assert(labmate_nav_tool_at(LabMateGroupComm, 0U) == LabMateToolUart);
    assert(strcmp(labmate_nav_tool_title(LabMateToolGenerator), "PWM Studio") == 0);
    assert(labmate_nav_tool_title(255U)[0] == '\0');
    assert(labmate_nav_group_title(255U)[0] == '\0');
    assert(labmate_nav_wrap(200U, 0U, 1) == 0U);
    assert(labmate_nav_wrap(255U, 3U, 1) == 1U);
    assert(labmate_nav_wrap(255U, 3U, -1) == 2U);
    /* Gate A: all menu selections stay visible within a 3-row viewport.
     * Exercise every reachable row, not only the historical spot checks. */
    for(uint8_t count = 1U; count <= 10U; ++count) {
        for(uint8_t selected = 0U; selected < count; ++selected) {
            const uint8_t start = labmate_nav_first_visible(selected, count, 3U);
            assert(start < count);
            assert(start <= selected);
            assert(selected < (uint8_t)(start + 3U));
            assert((uint8_t)(start + 3U) <=
                   (count > 3U ? count : 3U));
        }
    }
    /* Every grouped menu entry must fit its own viewport. */
    for(uint8_t group = 0U; group < LabMateGroupCount; ++group) {
        const uint8_t count = labmate_nav_group_size(group);
        for(uint8_t selected = 0U; selected < count; ++selected) {
            const uint8_t start = labmate_nav_first_visible(selected, count, 3U);
            assert(start <= selected && selected < (uint8_t)(start + 3U));
        }
    }
    puts("LabMate v2.0 baseline navigation: all 17 tools reachable once; SETTINGS last PASS");
    return 0;
}
