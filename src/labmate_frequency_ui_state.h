#pragma once
#include <stdbool.h>
/* Frequency UI is LIVE only after the correct native E11 engine holds
 * the capture owner. LOW uses EXTI, HIGH uses TIM2; a pending release,
 * competing engine, or denied resource invalidates the LIVE claim.
 * Pure C11, no HAL or GPIO reads.
 */
bool labmate_frequency_ui_live(
    bool high_pin, bool high_active, bool low_active,
    bool correct_owner, bool blocked, bool release_fault);
