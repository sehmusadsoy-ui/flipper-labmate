#include "labmate_frequency_tim2.h"

#include <furi_hal.h>
#include <furi_hal_resources.h>
#include <furi_hal_bus.h>
#include <stm32wbxx_ll_tim.h>

/* DEV E11.1d: claim the paired TIM2/PB3 lease before ANY peripheral write.
 * This is not a firmware-wide guarantee until other Momentum owners
 * participate in the same lease. A stock SDK must fail closed.
 */
static uint32_t labmate_tim2_lease_handle;
static bool labmate_tim2_configured;
static bool labmate_tim2_fault;

/* A legacy RFID/SubGHz/digital_sequence user can bypass the E11 table.
 * Detect an already enabled clock BEFORE PB3 mode or TIM2 writes; later
 * unexpected loss of our clock is a sticky fault, never a safe teardown.
 */
bool labmate_frequency_tim2_capture_valid(void) {
    if(!labmate_tim2_configured || !labmate_tim2_lease_handle ||
       labmate_tim2_fault) return false;
    if(!furi_hal_bus_is_enabled(FuriHalBusTIM2)) {
        labmate_tim2_fault = true; /* Keep the opaque firmware claim. */
        return false;
    }
    return true;
}

bool labmate_frequency_tim2_configure(void) {
    if(labmate_tim2_lease_handle || labmate_tim2_configured ||
       labmate_tim2_fault) return false;
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1)
    const uint32_t lease = furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3);
    if(lease == 0U) return false; /* NO GPIO, clock, TIM or IRQ writes. */
    labmate_tim2_lease_handle = lease;
    if(furi_hal_bus_is_enabled(FuriHalBusTIM2)) {
        /* Native RFID/SubGHz/digital-sequence clock already active.
         * The legacy bus enable API would assert on this state. Release
         * only our fresh claim; absolutely no GPIO or TIM2 register writes.
         */
        if(furi_hal_resource_lease_release(lease, FURI_HAL_LEASE_COUNTER_PB3)) {
            labmate_tim2_lease_handle = 0U;
        } else {
            labmate_tim2_fault = true; /* Do not retry a suspect token. */
        }
        return false;
    }
#else
    /* Never silently fall back to unsafe direct HAL on an older SDK. */
    return false;
#endif
    /* Keep the v1.6.1 TIM2_CH2 / PB3 rising-edge external clock setup. */
    furi_hal_gpio_init_ex(
        &gpio_ext_pb3,
        GpioModeAltFunctionPushPull,
        GpioPullNo,
        GpioSpeedVeryHigh,
        GpioAltFn1TIM2);

    furi_hal_bus_enable(FuriHalBusTIM2);

    LL_TIM_InitTypeDef timer_init = {0};
    timer_init.Prescaler = 0;
    timer_init.CounterMode = LL_TIM_COUNTERMODE_UP;
    timer_init.Autoreload = UINT32_MAX;
    timer_init.ClockDivision = LL_TIM_CLOCKDIVISION_DIV1;

    LL_TIM_Init(TIM2, &timer_init);
    LL_TIM_IC_SetActiveInput(TIM2, LL_TIM_CHANNEL_CH2, LL_TIM_ACTIVEINPUT_DIRECTTI);
    LL_TIM_IC_SetPrescaler(TIM2, LL_TIM_CHANNEL_CH2, LL_TIM_ICPSC_DIV1);
    LL_TIM_IC_SetPolarity(TIM2, LL_TIM_CHANNEL_CH2, LL_TIM_IC_POLARITY_RISING);
    LL_TIM_IC_SetFilter(TIM2, LL_TIM_CHANNEL_CH2, LL_TIM_IC_FILTER_FDIV1);
    LL_TIM_SetTriggerInput(TIM2, LL_TIM_TS_TI2FP2);
    LL_TIM_SetClockSource(TIM2, LL_TIM_CLOCKSOURCE_EXT_MODE1);
    LL_TIM_CC_EnableChannel(TIM2, LL_TIM_CHANNEL_CH2);
    LL_TIM_SetCounter(TIM2, 0);
    labmate_tim2_configured = true;
    return true;
}

/* Enable only after application state publishes the capture owner. */
void labmate_frequency_tim2_enable(void) {
    if(!labmate_frequency_tim2_capture_valid()) return;
    LL_TIM_EnableCounter(TIM2);
}

void labmate_frequency_tim2_disable(void) {
    if(!labmate_frequency_tim2_capture_valid()) return;
    LL_TIM_DisableCounter(TIM2);
}

uint32_t labmate_frequency_tim2_read(void) {
    if(!labmate_frequency_tim2_capture_valid()) return 0U;
    return LL_TIM_GetCounter(TIM2);
}

void labmate_frequency_tim2_shutdown(void) {
    if(!labmate_tim2_configured || labmate_tim2_lease_handle == 0U ||
       !labmate_frequency_tim2_capture_valid()) return;
    /* Keep the lease throughout teardown; only the owner resets TIM2/PB3.
     * The previously enabled clock must still be active, otherwise HAL
     * bus_disable may assert and resetting PB3 may corrupt a foreign user.
     */
    LL_TIM_DisableCounter(TIM2);
    LL_TIM_CC_DisableChannel(TIM2, LL_TIM_CHANNEL_CH2);
    furi_hal_bus_disable(FuriHalBusTIM2);
    furi_hal_gpio_init_simple(&gpio_ext_pb3, GpioModeAnalog);
    labmate_tim2_configured = false;
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1)
    if(furi_hal_resource_lease_release(
           labmate_tim2_lease_handle, FURI_HAL_LEASE_COUNTER_PB3)) {
        labmate_tim2_lease_handle = 0U;
    }
    else {
        labmate_tim2_fault = true; /* Fault is sticky until firmware reset. */
    }
    /* Release failure retains a blocking stale local handle, fail closed. */
#endif
}

bool labmate_frequency_tim2_lease_pending(void) {
    return labmate_tim2_lease_handle != 0U;
}
