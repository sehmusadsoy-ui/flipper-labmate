#pragma once

#include <stdint.h>
#include <stdbool.h>

/* Flat tool IDs remain stable: these map to the existing seven instrument
 * actions and the original 7-icon layout. Pure navigation, no GPIO/SD calls.
 */
typedef enum {
    LabMateToolGpio = 0,
    LabMateToolFrequency,
    LabMateToolPulse,
    LabMateToolGenerator,
    LabMateToolLogger,
    LabMateToolHistory,
    LabMateToolAbout,
    LabMateToolCount,
    LabMateToolInvalid = 255
} LabMateTool;

typedef enum {
    LabMateGroupMeasure = 0,
    LabMateGroupOutput,
    LabMateGroupRecords,
    LabMateGroupInfo,
    LabMateGroupCount
} LabMateMenuGroup;

#define LABMATE_NAV_MAX_CHILDREN 3U

uint8_t labmate_nav_group_size(uint8_t group);
uint8_t labmate_nav_tool_at(uint8_t group, uint8_t index);
uint8_t labmate_nav_group_icon(uint8_t group);
uint8_t labmate_nav_wrap(uint8_t current, uint8_t count, int8_t direction);
/* First visible row; small groups always show all of their tools. */
uint8_t labmate_nav_first_visible(uint8_t selected, uint8_t count, uint8_t rows);
const char* labmate_nav_group_title(uint8_t group);
const char* labmate_nav_tool_title(uint8_t tool);
