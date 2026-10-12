#pragma once
#include "labmate_internal.h"

/* LOW PC1 GPIO rising-edge and HIGH PB3 TIM2 capture lifecycles.
 * The shared core gates acquisition, and caller controls cross-tool stop order.
 */
void labmate_frequency_high_start(LabMateApp* app);
void labmate_frequency_high_stop(LabMateApp* app);
void labmate_frequency_low_start(LabMateApp* app);
void labmate_frequency_low_stop(LabMateApp* app);
