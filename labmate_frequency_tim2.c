#include "labmate_frequency_tim2.h"

#include <furi_hal.h>
#include <furi_hal_resources.h>
#include <furi_hal_bus.h>
#include <stm32wbxx_ll_tim.h>

void labmate_frequency_tim2_configure(void) {
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
}

/* Enable only after application state publishes the capture owner. */
void labmate_frequency_tim2_enable(void) {
    LL_TIM_EnableCounter(TIM2);
}

void labmate_frequency_tim2_disable(void) {
    LL_TIM_DisableCounter(TIM2);
}

uint32_t labmate_frequency_tim2_read(void) {
    return LL_TIM_GetCounter(TIM2);
}

void labmate_frequency_tim2_shutdown(void) {
    LL_TIM_DisableCounter(TIM2);
    LL_TIM_CC_DisableChannel(TIM2, LL_TIM_CHANNEL_CH2);
    furi_hal_bus_disable(FuriHalBusTIM2);
    furi_hal_gpio_init_simple(&gpio_ext_pb3, GpioModeAnalog);
}
