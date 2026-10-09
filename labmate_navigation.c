#include "labmate_navigation.h"

static const char* const group_titles[LabMateGroupCount] = {
    "MEASURE", "OUTPUT", "RECORDS", "INFO"
};

static const char* const tool_titles[LabMateToolCount] = {
    "GPIO Monitor",
    "Frequency Meter",
    "Pulse Analyzer",
    "Signal Generator",
    "Data Logger",
    "Log History",
    "About",
};

/* Each instrument remains reachable once, with its previous tool ID. */
static const uint8_t group_sizes[LabMateGroupCount] = {3U, 1U, 2U, 1U};
static const uint8_t group_tools[LabMateGroupCount][LABMATE_NAV_MAX_CHILDREN] = {
    {LabMateToolGpio, LabMateToolFrequency, LabMateToolPulse},
    {LabMateToolGenerator, LabMateToolInvalid, LabMateToolInvalid},
    {LabMateToolLogger, LabMateToolHistory, LabMateToolInvalid},
    {LabMateToolAbout, LabMateToolInvalid, LabMateToolInvalid}
};

uint8_t labmate_nav_group_size(uint8_t group) {
    return group < LabMateGroupCount ? group_sizes[group] : 0U;
}

uint8_t labmate_nav_tool_at(uint8_t group, uint8_t index) {
    return group < LabMateGroupCount && index < group_sizes[group]
               ? group_tools[group][index]
               : LabMateToolInvalid;
}

uint8_t labmate_nav_group_icon(uint8_t group) {
    return labmate_nav_tool_at(group, 0U);
}

uint8_t labmate_nav_wrap(uint8_t current, uint8_t count, int8_t direction) {
    if(count == 0U) return 0U;
    if(current >= count) current = 0U;
    if(direction > 0) return (uint8_t)((current + 1U) % count);
    if(direction < 0) return (uint8_t)((current + count - 1U) % count);
    return current;
}

const char* labmate_nav_group_title(uint8_t group) {
    return group < LabMateGroupCount ? group_titles[group] : "";
}

const char* labmate_nav_tool_title(uint8_t tool) {
    return tool < LabMateToolCount ? tool_titles[tool] : "";
}
