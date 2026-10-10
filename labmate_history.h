#pragma once

/* v1.6.1: read-only CSV Log History runtime, no output GPIO ownership.
 * Keep microSD I/O outside the UI mutex except for short app-state updates.
 */
#include "labmate_internal.h"

void labmate_history_scan(LabMateApp* app);
void labmate_history_open(LabMateApp* app);
void labmate_history_read_step(LabMateApp* app);
void labmate_history_close(LabMateApp* app);
