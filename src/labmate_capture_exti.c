#include "labmate_capture_exti.h"

#include <furi.h>
#include <stm32wbxx_ll_exti.h>

/* Preserve the tested v1.6.1 critical-section ordering. */
void labmate_capture_exti_clear(uint32_t line, bool clear_rising) {
    FURI_CRITICAL_ENTER();
    if(clear_rising) LL_EXTI_DisableRisingTrig_0_31(line);
    LL_EXTI_DisableFallingTrig_0_31(line);
    LL_EXTI_ClearFlag_0_31(line);
    FURI_CRITICAL_EXIT();
}
