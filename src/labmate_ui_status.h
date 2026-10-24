#pragma once
/* UI-06C — pure display status selection, no Flipper SDK/HAL dependency.
 * A badge represents current App state; it must never initiate a GPIO,
 * timer, generator, transport or microSD operation.
 */
#include <stdbool.h>

typedef enum {
    LabMateUiStatusLive = 0,
    LabMateUiStatusHold,
    LabMateUiStatusBusy,
    LabMateUiStatusError,
} LabMateUiStatus;

/* Priority matches the original GPIO Monitor renderer:
 * release error > tool/resource busy > hold > live.
 * Do not change these levels without a separate input/resource audit.
 */
static inline LabMateUiStatus labmate_ui_gpio_monitor_status(
    bool release_fault, bool blocked, bool hold) {
    if(release_fault) return LabMateUiStatusError;
    if(blocked) return LabMateUiStatusBusy;
    return hold ? LabMateUiStatusHold : LabMateUiStatusLive;
}

static inline const char* labmate_ui_status_label(LabMateUiStatus status) {
    switch(status) {
    case LabMateUiStatusLive: return "LIVE";
    case LabMateUiStatusHold: return "HOLD";
    case LabMateUiStatusBusy: return "BUSY";
    case LabMateUiStatusError: return "ERR";
    default: return "ERR"; /* Display unknown state conservatively. */
    }
}
