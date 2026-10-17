#pragma once
#include <stdbool.h>
#include <stdint.h>
#define FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK 1
typedef struct {uint32_t pin;} GpioPin;
typedef enum {GpioModeAnalog, GpioModeInterruptRiseFall} GpioMode;
typedef enum {GpioPullNo} GpioPull;
typedef enum {GpioSpeedVeryHigh} GpioSpeed;
typedef struct {uint32_t CTRL; uint32_t CYCCNT;} LabMateMockDwt;
extern LabMateMockDwt labmate_mock_dwt;
extern uint32_t SystemCoreClock;
#define DWT (&labmate_mock_dwt)
#define DWT_CTRL_CYCCNTENA_Msk (1UL << 0)
bool furi_hal_gpio_read(const GpioPin* pin);
bool furi_hal_gpio_try_add_int_callback(const GpioPin* pin, void (*callback)(void*), void* context);
void furi_hal_gpio_disable_int_callback(const GpioPin* pin);
void furi_hal_gpio_enable_int_callback(const GpioPin* pin);
void furi_hal_gpio_remove_int_callback(const GpioPin* pin);
void furi_hal_gpio_init(const GpioPin* pin, GpioMode mode, GpioPull pull, GpioSpeed speed);
void furi_hal_gpio_init_simple(const GpioPin* pin, GpioMode mode);
