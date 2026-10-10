#pragma once

/* Owns CSV file start/stop, numbering and microSD handle lifecycle.
 * Acquisition, 1 s row scheduling and GUI mutex remain in the app core.
 */
#include "labmate_internal.h"

bool labmate_logger_storage_start(LabMateApp* app);
void labmate_logger_storage_stop(LabMateApp* app);
