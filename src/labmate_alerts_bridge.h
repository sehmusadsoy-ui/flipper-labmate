#pragma once
#include "labmate_internal.h"
/* Sample validity gating; only the app thread calls this. */
void threshold_update_from_measurement(LabMateApp* app);
