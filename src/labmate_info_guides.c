#include "labmate_info_guides.h"
#include "labmate_navigation.h"

/* Purpose / wiring / controls are the approved Step 0 mapping of all 17
 * original help records. UI-only copy; no implied electrical guarantees. */
static const LabMateInfoGuide guides[LABMATE_INFO_GUIDE_COUNT] = {
    [LabMateToolGpio] = {
        .title = "GPIO monitor", .icon = UiKitIconGpio,
        .summary = {"Watch eight pins", "go high or low."},
        .chips = {{"PC0", "PC1", "PC3", "PB2"}, {"PB3", "PA4", "PA6", "PA7"}},
        .chip_rows = 2,
        .facts = {"Eight logic pins", "Checks pin changes"}, .fact_count = 2,
        .controls = {{UiKitKeyLeftRight, "Pin"}, {UiKitKeyOk, "Hold"},
                     {UiKitKeyBack, "Exit"}}, .control_count = 3,
    },
    [LabMateToolFrequency] = {
        .title = "Frequency meter", .short_title = "Frequency", .icon = UiKitIconFreq,
        .summary = {"Measure how often a", "signal repeats."},
        .chips = {{"PC1 low", "PB3 high"}}, .chip_rows = 1,
        .facts = {"Period or counts", "Two input modes"}, .fact_count = 2,
        .controls = {{UiKitKeyLeftRight, "Mode"}, {UiKitKeyUp, "Reset stats"},
                     {UiKitKeyOk, "Hold"}}, .control_count = 3,
    },
    [LabMateToolPulse] = {
        .title = "Pulse analyzer", .short_title = "Pulse", .icon = UiKitIconFreq,
        .summary = {"Measure pulse width", "and duty cycle."},
        .chips = {{"PC0", "PC1", "PB2", "PA4"}}, .chip_rows = 1,
        .facts = {"High / low / period", "Duty percentage"}, .fact_count = 2,
        .controls = {{UiKitKeyLeftRight, "Pin"}, {UiKitKeyUp, "Stats"},
                     {UiKitKeyDown, "Reset"}, {UiKitKeyOk, "Hold"}}, .control_count = 4,
    },
    [LabMateToolGenerator] = {
        .title = "PWM studio", .icon = UiKitIconPwm,
        .summary = {"Generate a square", "wave from PA7."},
        .chips = {{"PA7 output", "3.3 V"}}, .chip_rows = 1,
        .facts = {"1 Hz to 50 kHz", "5-95% duty cycle"}, .fact_count = 2,
        .controls = {{UiKitKeyLeftRight, "Frequency"}, {UiKitKeyUpDown, "Duty"},
                     {UiKitKeyOk, "Start / Stop"}, {UiKitKeyOkHold, "Edit"}},
        .control_count = 4,
    },
    [LabMateToolLogger] = {
        .title = "Data logger", .icon = UiKitIconRec,
        .summary = {"Save measurements", "as CSV files on SD."},
        .chips = {{"PC1 low", "PC1 pulse"}, {"PB3 high"}}, .chip_rows = 2,
        .facts = {"Samples every 1 s", "CSV saved on SD"}, .fact_count = 2,
        .controls = {{UiKitKeyLeftRight, "Source"}, {UiKitKeyOk, "Record / Stop"},
                     {UiKitKeyBack, "Exit"}}, .control_count = 3,
    },
    [LabMateToolHistory] = {
        .title = "Log history", .icon = UiKitIconRec,
        .summary = {"Review or delete", "saved CSV readings."},
        .chips = {{"Saved CSV", "SD card"}}, .chip_rows = 1,
        .facts = {"Open or delete logs", "Confirm deletions"}, .fact_count = 2,
        .controls = {{UiKitKeyUpDown, "Choose log"},
                     {UiKitKeyLeftRight, "Open / Delete"},
                     {UiKitKeyOk, "Select"}}, .control_count = 3,
    },
    [LabMateToolAbout] = {
        .title = "Using LabMate", .short_title = "Guide", .icon = UiKitIconInfo,
        .summary = {"Find tool help and", "project details."},
        .chips = {{"17 guides", "Project"}, {"Safety"}}, .chip_rows = 2,
        .facts = {"No external pins", "Info and links"}, .fact_count = 2,
        .controls = {{UiKitKeyUpDown, "Browse"}, {UiKitKeyOk, "Open"},
                     {UiKitKeyBack, "Menu"}}, .control_count = 3,
    },
    [LabMateToolProfiles] = {
        .title = "Profiles", .icon = UiKitIconDash,
        .summary = {"Save three device", "setups for later."},
        .chips = {{"S1", "S2", "S3"}}, .chip_rows = 1,
        .facts = {"Load, save, delete", "PWM stays stopped"}, .fact_count = 2,
        .controls = {{UiKitKeyUpDown, "Slot"}, {UiKitKeyLeftRight, "Action"},
                     {UiKitKeyOk, "Select"}}, .control_count = 3,
    },
    [LabMateToolCounter] = {
        /* The existing shared icon guard treats UiKitIconCount as the end
         * marker. Use the established frequency glyph without changing the
         * accepted menu's rendering in this Info-only stage. */
        .title = "Event counter", .short_title = "Counter", .icon = UiKitIconFreq,
        .summary = {"Count rising signal", "changes over time."},
        .chips = {{"PB3"}}, .chip_rows = 1,
        .facts = {"64-bit count", "Elapsed time shown"}, .fact_count = 2,
        .controls = {{UiKitKeyOk, "Start / Stop"}, {UiKitKeyUp, "Reset"},
                     {UiKitKeyBack, "Exit"}}, .control_count = 3,
    },
    [LabMateToolButton] = {
        .title = "Button analyzer", .short_title = "Button", .icon = UiKitIconGpio,
        .summary = {"Check switch input", "and contact bounce."},
        .chips = {{"PC1 input", "Pull-up"}}, .chip_rows = 1,
        .facts = {"Low means pressed", "Bounce / settle"}, .fact_count = 2,
        .controls = {{UiKitKeyOk, "Start / Stop"}, {UiKitKeyLeftRight, "Quiet time"},
                     {UiKitKeyDown, "Details"}, {UiKitKeyUp, "Reset"}},
        .control_count = 4,
    },
    [LabMateToolAlerts] = {
        .title = "Threshold alerts", .short_title = "Alerts", .icon = UiKitIconDoctor,
        .summary = {"Watch readings for", "limits you choose."},
        .chips = {{"Frequency", "Duty"}, {"Count", "Settle"}}, .chip_rows = 2,
        .facts = {"Alert stays set", "Until acknowledged"}, .fact_count = 2,
        .controls = {{UiKitKeyLeftRight, "Source"}, {UiKitKeyUpDown, "Limit when off"},
                     {UiKitKeyOk, "Arm"}, {UiKitKeyDown, "Clear when armed"}},
        .control_count = 4,
    },
    [LabMateToolUart] = {
        .title = "UART terminal", .short_title = "UART", .icon = UiKitIconUart,
        .summary = {"Send and read data", "over a serial link."},
        .chips = {{"Pin 13 TX"}, {"Pin 14 RX"}, {"3.3 V"}}, .chip_rows = 3,
        .facts = {"9600-115200 / 8N1", "Serial messages"}, .fact_count = 2,
        .controls = {{UiKitKeyLeftRight, "Baud"}, {UiKitKeyOk, "Start / Stop"},
                     {UiKitKeyUp, "Clear"}, {UiKitKeyDown, "Edit TX"}},
        .control_count = 4,
    },
    [LabMateToolOneWire] = {
        .title = "1-Wire temp", .icon = UiKitIconI2c,
        .summary = {"Read an external", "temperature sensor."},
        .chips = {{"PA4 data"}, {"3.3 V supply"}}, .chip_rows = 2,
        .facts = {"External sensor VDD", "1-Wire data pin"}, .fact_count = 2,
        .controls = {{UiKitKeyOk, "Read / Stop"}, {UiKitKeyBack, "Exit"}},
        .control_count = 2,
    },
    [LabMateToolI2c] = {
        .title = "I2C explorer", .icon = UiKitIconI2c,
        .summary = {"Find devices on a", "3.3 V I2C bus."},
        .chips = {{"PC0 clock"}, {"PC1 data"}, {"3.3 V bus"}}, .chip_rows = 3,
        .facts = {"Exclusive 3.3 V bus", "Scan bus devices"}, .fact_count = 2,
        .controls = {{UiKitKeyOk, "Scan / Stop"}, {UiKitKeyUpDown, "Pages"},
                     {UiKitKeyBack, "Exit"}}, .control_count = 3,
    },
    [LabMateToolScope] = {
        .title = "Logic scope", .icon = UiKitIconScope,
        .summary = {"Watch signal timing", "from a PC1 capture."},
        .chips = {{"PC1", "3.3 V digital"}}, .chip_rows = 1,
        .facts = {"Measured edges only", "Save two captures"}, .fact_count = 2,
        .controls = {{UiKitKeyOk, "Capture / Stop"}, {UiKitKeyDown, "Pages"},
                     {UiKitKeyLeftRight, "Save A / B"}, {UiKitKeyBack, "Exit"}},
        .control_count = 4,
    },
    [LabMateToolDoctor] = {
        .title = "Signal doctor", .short_title = "Doctor", .icon = UiKitIconDoctor,
        .summary = {"Compare samples", "to your reference."},
        .chips = {{"Saved capture"}, {"User reference"}}, .chip_rows = 2,
        .facts = {"User-set reference", "Advisory results"}, .fact_count = 2,
        .controls = {{UiKitKeyLeftRight, "Pages"}, {UiKitKeyUpDown, "Setup row"},
                     {UiKitKeyOk, "Edit"}, {UiKitKeyOkHold, "Help"}},
        .control_count = 4,
    },
    [LabMateToolDashboard] = {
        .title = "Dashboard", .icon = UiKitIconDash,
        .summary = {"Review past data", "in one place."},
        .chips = {{"Frequency", "Pulse"}, {"Scope", "Count", "Logs"}},
        .chip_rows = 2,
        .facts = {"Read-only overview", "Past values / stats"}, .fact_count = 2,
        .controls = {{UiKitKeyUpDown, "Source"}, {UiKitKeyLeftRight, "Group"},
                     {UiKitKeyOk, "Details"}}, .control_count = 3,
    },
};

const LabMateInfoGuide* labmate_info_guide(uint8_t index) {
    return index < LABMATE_INFO_GUIDE_COUNT ? &guides[index] : NULL;
}

uint8_t labmate_info_guide_max_scroll_steps(uint8_t index) {
    const LabMateInfoGuide* guide = labmate_info_guide(index);
    if(!guide || !guide->control_count) return 0U;
    /* Title y15; two purpose lines y35,43; chip lines y46+12n;
     * facts y+7/+16; controls after +2. These positions match the renderer. */
    const uint16_t control_top = 46U + 12U * guide->chip_rows +
                                 9U * guide->fact_count + 2U;
    const uint16_t last_bottom = control_top +
                                 12U * (guide->control_count - 1U) + 10U;
    return last_bottom > 64U ? (uint8_t)((last_bottom - 64U + 11U) / 12U) : 0U;
}
