#include <furi.h>
#include <furi_hal.h>
#include <furi_hal_resources.h>
#include <furi_hal_pwm.h>
#include <furi_hal_bus.h>
#include <stm32wbxx_ll_tim.h>
#include <stm32wbxx_ll_exti.h>
#include <gui/gui.h>
#include <input/input.h>

#define MENU_COUNT 5
#define GPIO_COUNT 8


typedef enum {
    LabMateScreenMenu,
    LabMateScreenGpio,
    LabMateScreenFrequency,
    LabMateScreenPulse,
    LabMateScreenGenerator,
    LabMateScreenAbout,
} LabMateScreen;

typedef struct {
    bool running;
    bool hold;

    uint8_t selected;
    uint8_t gpio_index;

    LabMateScreen screen;

    bool gpio_state;
    bool gpio_previous_state;
    uint32_t edges;

    /* Frequency meter */
    uint32_t frequency_last_edge;
    uint32_t frequency_period_ticks;
    uint32_t frequency_millihz;
    bool frequency_edge_seen;
    bool frequency_valid;
    /* v1.4-dev: running minimum and maximum of valid frequency readings.
     * Units are millihertz (same as frequency_millihz). */
    uint32_t frequency_min_millihz;
    uint32_t frequency_max_millihz;
    bool frequency_stats_valid;

    volatile uint32_t frequency_irq_last_cycle;
    volatile uint32_t frequency_irq_period_cycles;
    volatile uint32_t frequency_irq_last_tick;
    volatile uint32_t frequency_irq_edges;
    volatile bool frequency_irq_new_period;
    volatile uint32_t frequency_irq_cycle_accumulator;
    volatile uint8_t frequency_irq_accumulated_periods;
    bool frequency_irq_active;

    /* High-frequency hardware counter on PB3 / TIM2_CH2 */
    bool frequency_hw_active;
    uint32_t frequency_hw_last_count;
    uint32_t frequency_hw_last_cycle;

    uint32_t frequency_period_samples[8];
    uint8_t frequency_sample_index;
    uint8_t frequency_sample_count;

    /* Pulse analyzer: edge timestamps captured in GPIO IRQ. */
    bool pulse_irq_active;
    volatile bool pulse_irq_level;
    volatile bool pulse_irq_seen;
    volatile bool pulse_irq_high_valid;
    volatile bool pulse_irq_low_valid;
    volatile uint32_t pulse_irq_last_cycle;
    volatile uint32_t pulse_irq_last_tick;
    volatile uint32_t pulse_irq_tick_cycle;
    volatile uint32_t pulse_irq_high_cycles;
    volatile uint32_t pulse_irq_low_cycles;
    volatile uint32_t pulse_irq_edges;
    /* Short block averages suppress high-frequency ISR timestamp jitter.
     * Only used when the measured half-period is <= 1 ms. */
    volatile uint32_t pulse_irq_high_sum;
    volatile uint32_t pulse_irq_low_sum;
    volatile uint8_t pulse_irq_high_samples;
    volatile uint8_t pulse_irq_low_samples;
    volatile bool pulse_irq_wide_window;

    /* Display-side snapshot: no IRQ writes to these fields. */
    uint32_t pulse_high_cycles;
    uint32_t pulse_low_cycles;
    uint32_t pulse_period_cycles;
    uint32_t pulse_duty_permille;
    bool pulse_high_valid;
    bool pulse_low_valid;
    bool pulse_period_valid;

    /* v1.4: Pulse Analyzer extrema come from completed display-side
     * measurements. Never update this history from the GPIO interrupt. */
    bool pulse_stats_view;
    bool pulse_stats_valid;
    bool pulse_stats_last_valid;
    uint32_t pulse_stats_last_high_cycles;
    uint32_t pulse_stats_last_low_cycles;
    uint32_t pulse_min_high_cycles;
    uint32_t pulse_max_high_cycles;
    uint32_t pulse_min_low_cycles;
    uint32_t pulse_max_low_cycles;
    uint32_t pulse_min_period_cycles;
    uint32_t pulse_max_period_cycles;
    uint32_t pulse_min_duty_permille;
    uint32_t pulse_max_duty_permille;

    /* Signal generator */
    bool generator_running;
    bool generator_state;
    uint8_t generator_freq_index;
    uint32_t generator_last_toggle;

    FuriMutex* mutex;
} LabMateApp;

static const char* menu_items[MENU_COUNT] = {
    "GPIO Monitor",
    "Frequency Meter",
    "Pulse Analyzer",
    "Signal Generator",
    "About",
};

static const GpioPin* labmate_gpio_pins[GPIO_COUNT] = {
    &gpio_ext_pc0,
    &gpio_ext_pc1,
    &gpio_ext_pc3,
    &gpio_ext_pb2,
    &gpio_ext_pb3,
    &gpio_ext_pa4,
    &gpio_ext_pa6,
    &gpio_ext_pa7,
};

static const char* gpio_names[GPIO_COUNT] = {
    "PC0",
    "PC1",
    "PC3",
    "PB2",
    "PB3",
    "PA4",
    "PA6",
    "PA7",
};

/* Pulse Analyzer uses GPIO edge interrupts, not polling.
 * STM32 EXTI lines are shared across GPIO ports, and the firmware already
 * uses EXTI3 for the OK button and EXTI6 for the DOWN button.
 * Therefore PC3/PB3 (line 3) and PA6 (line 6) MUST NOT be armed as IRQ
 * sources by this app. PA7 is also reserved for the signal generator.
 * GPIO Monitor retains all eight pins because it uses polling.
 *
 * Valid Pulse Analyzer input pins: PC0, PC1, PB2, PA4.
 */
static const uint8_t pulse_gpio_indices[] = {0U, 1U, 3U, 5U};
#define PULSE_GPIO_COUNT (sizeof(pulse_gpio_indices) / sizeof(pulse_gpio_indices[0]))

static uint8_t pulse_gpio_next_index(uint8_t current, int8_t direction) {
    size_t i = 0;
    for(; i < PULSE_GPIO_COUNT; i++) {
        if(pulse_gpio_indices[i] == current) break;
    }
    /* A previous tool may have selected a pin unavailable for IRQ capture. */
    if(i == PULSE_GPIO_COUNT) return 1U; /* PC1 */
    if(direction > 0) {
        i = (i + 1U) % PULSE_GPIO_COUNT;
    } else {
        i = (i + PULSE_GPIO_COUNT - 1U) % PULSE_GPIO_COUNT;
    }
    return pulse_gpio_indices[i];
}

/*
 * Conservative self-test frequencies.
 * Designed for the current polling-based
 * measurement engine.
 */
static const uint32_t generator_frequencies[] = {
    1,
    2,
    5,
    10,
    20,
    50,
    100,
    200,
    500,
    1000,
    2000,
    5000,
    10000,
    20000,
    50000,
};

#define GENERATOR_FREQ_COUNT 15

static void frequency_gpio_callback(void* context) {
    LabMateApp* app = context;

    /*
     * High-resolution timestamp.
     * Unsigned subtraction also handles a single
     * 32-bit CYCCNT wrap correctly.
     */
    uint32_t now_cycle = DWT->CYCCNT;

    if(app->frequency_irq_last_cycle != 0) {
        uint32_t period_cycles =
            now_cycle -
            app->frequency_irq_last_cycle;

        /*
         * Above roughly 1 kHz, average 32 complete
         * periods inside the ISR before publishing.
         * This reduces interrupt timing jitter.
         */
        if(SystemCoreClock > 0 &&
           period_cycles <
               (SystemCoreClock / 1000U)) {

            app->frequency_irq_cycle_accumulator +=
                period_cycles;

            app->frequency_irq_accumulated_periods++;

            if(app->frequency_irq_accumulated_periods >= 32U) {
                app->frequency_irq_period_cycles =
                    (app->frequency_irq_cycle_accumulator +
                     16U) /
                    32U;

                app->frequency_irq_new_period = true;

                app->frequency_irq_cycle_accumulator = 0;
                app->frequency_irq_accumulated_periods = 0;
            }
        } else {
            app->frequency_irq_cycle_accumulator = 0;
            app->frequency_irq_accumulated_periods = 0;

            app->frequency_irq_period_cycles =
                period_cycles;

            app->frequency_irq_new_period = true;
        }
    }

    app->frequency_irq_last_cycle = now_cycle;
    app->frequency_irq_last_tick = furi_get_tick();
    app->frequency_irq_edges++;
}

static void frequency_hw_stop(LabMateApp* app) {
    if(!app->frequency_hw_active) {
        return;
    }

    LL_TIM_DisableCounter(TIM2);
    LL_TIM_CC_DisableChannel(TIM2, LL_TIM_CHANNEL_CH2);

    furi_hal_bus_disable(FuriHalBusTIM2);

    furi_hal_gpio_init_simple(
        &gpio_ext_pb3,
        GpioModeAnalog);

    app->frequency_hw_active = false;
    app->frequency_hw_last_count = 0;
    app->frequency_hw_last_cycle = 0;
}

static void frequency_hw_start(LabMateApp* app) {
    if(app->frequency_hw_active) {
        return;
    }

    /*
     * PB3 -> TIM2_CH2
     * TIM2 counts incoming rising edges directly in hardware.
     * No interrupt is generated for each edge.
     */
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

    LL_TIM_IC_SetActiveInput(
        TIM2,
        LL_TIM_CHANNEL_CH2,
        LL_TIM_ACTIVEINPUT_DIRECTTI);

    LL_TIM_IC_SetPrescaler(
        TIM2,
        LL_TIM_CHANNEL_CH2,
        LL_TIM_ICPSC_DIV1);

    LL_TIM_IC_SetPolarity(
        TIM2,
        LL_TIM_CHANNEL_CH2,
        LL_TIM_IC_POLARITY_RISING);

    LL_TIM_IC_SetFilter(
        TIM2,
        LL_TIM_CHANNEL_CH2,
        LL_TIM_IC_FILTER_FDIV1);

    LL_TIM_SetTriggerInput(
        TIM2,
        LL_TIM_TS_TI2FP2);

    LL_TIM_SetClockSource(
        TIM2,
        LL_TIM_CLOCKSOURCE_EXT_MODE1);

    LL_TIM_CC_EnableChannel(
        TIM2,
        LL_TIM_CHANNEL_CH2);

    LL_TIM_SetCounter(TIM2, 0);

    app->frequency_hw_last_count = 0;
    app->frequency_hw_last_cycle = DWT->CYCCNT;
    app->frequency_hw_active = true;

    LL_TIM_EnableCounter(TIM2);
}
static void __attribute__((unused)) frequency_interrupt_stop(LabMateApp* app) {
    if(!app->frequency_irq_active) return;

    const GpioPin* pin =
        labmate_gpio_pins[app->gpio_index];

    furi_hal_gpio_disable_int_callback(pin);
    furi_hal_gpio_remove_int_callback(pin);

    app->frequency_irq_active = false;
}

static void __attribute__((unused)) frequency_interrupt_start(LabMateApp* app) {
    const GpioPin* pin =
        labmate_gpio_pins[app->gpio_index];

    app->frequency_irq_last_cycle = 0;
    app->frequency_irq_period_cycles = 0;
    app->frequency_irq_last_tick = 0;
    app->frequency_irq_edges = 0;
    app->frequency_irq_new_period = false;

    /* Explicitly clear the old falling-edge trigger. Momentum's GPIO init
     * enables rising interrupts but does not always clear falling triggers
     * left by Pulse Analyzer's previous rise/fall EXTI configuration.
     * Without this, a 1 kHz square wave may appear as 2 kHz here.
     */
    FURI_CRITICAL_ENTER();
    LL_EXTI_DisableFallingTrig_0_31(LL_EXTI_LINE_1);
    LL_EXTI_ClearFlag_0_31(LL_EXTI_LINE_1);
    FURI_CRITICAL_EXIT();

    furi_hal_gpio_init(
        pin,
        GpioModeInterruptRise,
        GpioPullNo,
        GpioSpeedVeryHigh);

    furi_hal_gpio_add_int_callback(
        pin,
        frequency_gpio_callback,
        app);

    furi_hal_gpio_enable_int_callback(pin);

    app->frequency_irq_active = true;
}

/* Pulse Analyzer uses BOTH edges and the CPU cycle counter.
 * ISR only captures timestamps; all arithmetic stays in the app thread.
 * Like other GPIO tools, it is intended for 3.3V digital signals only.
 */
static void pulse_gpio_callback(void* context) {
    LabMateApp* app = context;
    const GpioPin* pin = labmate_gpio_pins[app->gpio_index];
    const uint32_t cycle = DWT->CYCCNT;
    const bool level = furi_hal_gpio_read(pin);

    if(level == app->pulse_irq_level) return;

    if(app->pulse_irq_seen) {
        const uint32_t delta = cycle - app->pulse_irq_last_cycle;
        if(delta > 0U) {
            /* At ordinary frequencies preserve the 16-sample response.
             * For very short pulses, collect 128 HIGH and 128 LOW widths
             * and publish them TOGETHER. Independent publications could
             * otherwise mix widths from different moments on the LCD.
             * This reduces random timing jitter, not systematic latency.
             */
            const uint32_t fast_half_period = SystemCoreClock / 1000U;
            const uint32_t short_half_period = SystemCoreClock / 25000U;
            const bool wide_window =
                short_half_period > 0U && delta <= short_half_period;

            if(app->pulse_irq_wide_window != wide_window) {
                app->pulse_irq_high_sum = 0U;
                app->pulse_irq_low_sum = 0U;
                app->pulse_irq_high_samples = 0U;
                app->pulse_irq_low_samples = 0U;
                app->pulse_irq_wide_window = wide_window;
            }

            if(fast_half_period > 0U && delta <= fast_half_period) {
                if(app->pulse_irq_level) {
                    app->pulse_irq_high_sum += delta;
                    ++app->pulse_irq_high_samples;
                    if(!wide_window && app->pulse_irq_high_samples >= 16U) {
                        app->pulse_irq_high_cycles =
                            (app->pulse_irq_high_sum + 8U) >> 4;
                        app->pulse_irq_high_valid = true;
                        app->pulse_irq_high_sum = 0U;
                        app->pulse_irq_high_samples = 0U;
                    }
                } else {
                    app->pulse_irq_low_sum += delta;
                    ++app->pulse_irq_low_samples;
                    if(!wide_window && app->pulse_irq_low_samples >= 16U) {
                        app->pulse_irq_low_cycles =
                            (app->pulse_irq_low_sum + 8U) >> 4;
                        app->pulse_irq_low_valid = true;
                        app->pulse_irq_low_sum = 0U;
                        app->pulse_irq_low_samples = 0U;
                    }
                }

                if(wide_window &&
                   app->pulse_irq_high_samples >= 128U &&
                   app->pulse_irq_low_samples >= 128U) {
                    app->pulse_irq_high_cycles =
                        (app->pulse_irq_high_sum +
                         app->pulse_irq_high_samples / 2U) /
                        app->pulse_irq_high_samples;
                    app->pulse_irq_low_cycles =
                        (app->pulse_irq_low_sum +
                         app->pulse_irq_low_samples / 2U) /
                        app->pulse_irq_low_samples;
                    app->pulse_irq_high_valid = true;
                    app->pulse_irq_low_valid = true;
                    app->pulse_irq_high_sum = 0U;
                    app->pulse_irq_low_sum = 0U;
                    app->pulse_irq_high_samples = 0U;
                    app->pulse_irq_low_samples = 0U;
                }
            } else {
                app->pulse_irq_high_sum = 0U;
                app->pulse_irq_low_sum = 0U;
                app->pulse_irq_high_samples = 0U;
                app->pulse_irq_low_samples = 0U;
                if(app->pulse_irq_level) {
                    app->pulse_irq_high_cycles = delta;
                    app->pulse_irq_high_valid = true;
                } else {
                    app->pulse_irq_low_cycles = delta;
                    app->pulse_irq_low_valid = true;
                }
            }
        }
    }

    app->pulse_irq_level = level;
    app->pulse_irq_seen = true;
    app->pulse_irq_last_cycle = cycle;
    /* Avoid a kernel tick call on every edge (20,000 IRQ/s at 10 kHz).
     * Refresh the stale-signal timestamp at most once every 10 ms.
     * A slow signal still updates it on each edge.
     */
    const uint32_t tick_gap_cycles = SystemCoreClock / 100U;
    if(tick_gap_cycles == 0U ||
       (uint32_t)(cycle - app->pulse_irq_tick_cycle) >= tick_gap_cycles) {
        app->pulse_irq_last_tick = furi_get_tick();
        app->pulse_irq_tick_cycle = cycle;
    }
    app->pulse_irq_edges++;
}

static void pulse_interrupt_stop(LabMateApp* app) {
    if(!app->pulse_irq_active) return;
    const GpioPin* pin = labmate_gpio_pins[app->gpio_index];
    furi_hal_gpio_disable_int_callback(pin);
    furi_hal_gpio_remove_int_callback(pin);

    /* Release both EXTI edge triggers as well as the callback. Merely
     * removing an interrupt callback leaves the rising/falling trigger
     * configuration behind on this firmware version.
     */
    FURI_CRITICAL_ENTER();
    LL_EXTI_DisableRisingTrig_0_31((uint32_t)pin->pin);
    LL_EXTI_DisableFallingTrig_0_31((uint32_t)pin->pin);
    LL_EXTI_ClearFlag_0_31((uint32_t)pin->pin);
    FURI_CRITICAL_EXIT();
    app->pulse_irq_active = false;
}

static void pulse_interrupt_start(LabMateApp* app) {
    const GpioPin* pin = labmate_gpio_pins[app->gpio_index];
    if(app->pulse_irq_active) return;

    app->pulse_irq_seen = false;
    app->pulse_irq_high_valid = false;
    app->pulse_irq_low_valid = false;
    app->pulse_irq_high_cycles = 0;
    app->pulse_irq_low_cycles = 0;
    app->pulse_irq_edges = 0;
    app->pulse_irq_high_sum = 0;
    app->pulse_irq_low_sum = 0;
    app->pulse_irq_high_samples = 0;
    app->pulse_irq_low_samples = 0;
    app->pulse_irq_wide_window = false;

    furi_hal_gpio_init(
        pin, GpioModeInterruptRiseFall, GpioPullNo, GpioSpeedVeryHigh);
    app->pulse_irq_level = furi_hal_gpio_read(pin);
    app->pulse_irq_last_cycle = DWT->CYCCNT;
    app->pulse_irq_tick_cycle = app->pulse_irq_last_cycle;
    app->pulse_irq_last_tick = furi_get_tick();

    furi_hal_gpio_add_int_callback(pin, pulse_gpio_callback, app);
    furi_hal_gpio_enable_int_callback(pin);
    app->pulse_irq_active = true;
}

static void gpio_release(uint8_t index) {
    furi_hal_gpio_init_simple(
        labmate_gpio_pins[index],
        GpioModeAnalog);
}

static void measurement_reset(LabMateApp* app) {
    uint32_t now = furi_get_tick();

    app->edges = 0;

    app->frequency_last_edge = now;
    app->frequency_period_ticks = 0;
    app->frequency_millihz = 0;
    app->frequency_edge_seen = false;
    app->frequency_valid = false;

    memset(
        app->frequency_period_samples,
        0,
        sizeof(app->frequency_period_samples));

    app->frequency_sample_index = 0;
    app->frequency_sample_count = 0;
    app->frequency_irq_cycle_accumulator = 0;
    app->frequency_irq_accumulated_periods = 0;

    app->pulse_high_cycles = 0;
    app->pulse_low_cycles = 0;
    app->pulse_period_cycles = 0;
    app->pulse_duty_permille = 0;

    app->pulse_high_valid = false;
    app->pulse_low_valid = false;
    app->pulse_period_valid = false;
}

/* Frequency extrema are scoped to one meter session and one input mode.
 * HOLD and signal loss keep extrema; UP or mode re-entry clears them. */
static void frequency_stats_reset(LabMateApp* app) {
    app->frequency_min_millihz = 0U;
    app->frequency_max_millihz = 0U;
    app->frequency_stats_valid = false;
}

/* Called once per new valid measurement, never on an old/stale reading. */
static void frequency_stats_record(LabMateApp* app) {
    if(!app->frequency_valid || app->frequency_millihz == 0U) return;

    const uint32_t sample = app->frequency_millihz;
    if(!app->frequency_stats_valid) {
        app->frequency_min_millihz = sample;
        app->frequency_max_millihz = sample;
        app->frequency_stats_valid = true;
    } else {
        if(sample < app->frequency_min_millihz) app->frequency_min_millihz = sample;
        if(sample > app->frequency_max_millihz) app->frequency_max_millihz = sample;
    }
}

/* Forward declaration: pin selection can reset statistics before their helper definition. */
static void pulse_stats_reset(LabMateApp* app);

static void gpio_activate(LabMateApp* app) {
    furi_hal_gpio_init_simple(
        labmate_gpio_pins[app->gpio_index],
        GpioModeInput);

    app->gpio_state =
        furi_hal_gpio_read(
            labmate_gpio_pins[app->gpio_index]);

    app->gpio_previous_state =
        app->gpio_state;

    measurement_reset(app);
}

static void gpio_change(
    LabMateApp* app,
    int8_t direction) {

    /*
     * Frequency Meter has two stable measurement modes:
     *
     * LEFT  -> PC1 / low-frequency period measurement
     * RIGHT -> PB3 / TIM2 hardware edge counter
     */
    if(app->screen == LabMateScreenFrequency) {
        uint8_t target_index =
            (direction > 0) ? 4U : 1U; /* PB3 : PC1 */

        if(app->gpio_index == target_index) {
            return;
        }

        frequency_interrupt_stop(app);
        frequency_hw_stop(app);

        gpio_release(app->gpio_index);

        app->gpio_index = target_index;
        app->hold = false;

        frequency_stats_reset(app);
        measurement_reset(app);

        if(app->gpio_index == 4U) {
            frequency_hw_start(app);
        } else {
            frequency_interrupt_start(app);
        }

        return;
    }

    if(app->screen == LabMateScreenPulse) {
        const uint8_t next_index = pulse_gpio_next_index(app->gpio_index, direction);
        if(next_index == app->gpio_index) return;
        /* Detach the old EXTI callback before changing pin or IRQ state. */
        pulse_interrupt_stop(app);
        gpio_release(app->gpio_index);
        app->gpio_index = next_index;
        app->hold = false;
        app->pulse_stats_view = false;
        pulse_stats_reset(app);
        measurement_reset(app);
        pulse_interrupt_start(app);
        return;
    }

    gpio_release(app->gpio_index);

    if(direction > 0) {
        app->gpio_index++;

        if(app->gpio_index >= GPIO_COUNT) {
            app->gpio_index = 0;
        }
    } else {
        if(app->gpio_index == 0) {
            app->gpio_index = GPIO_COUNT - 1;
        } else {
            app->gpio_index--;
        }
    }

    gpio_activate(app);
}

/* Convert captured CPU cycles with 64-bit intermediates. */
static uint64_t pulse_cycles_to_us(uint32_t cycles) {
    if(SystemCoreClock == 0U) return 0;
    return (((uint64_t)cycles * 1000000ULL) +
            (SystemCoreClock / 2U)) / SystemCoreClock;
}

static void pulse_recalculate(LabMateApp* app) {
    app->pulse_period_valid = false;
    if(!app->pulse_high_valid || !app->pulse_low_valid) return;

    uint64_t period =
        (uint64_t)app->pulse_high_cycles + app->pulse_low_cycles;
    if(period == 0 || period > UINT32_MAX) return;

    app->pulse_period_cycles = (uint32_t)period;
    app->pulse_duty_permille = (uint32_t)(
        ((uint64_t)app->pulse_high_cycles * 1000ULL + period / 2ULL) /
        period);
    app->pulse_period_valid = true;
}

/* The extrema summarize published/averaged HIGH+LOW readings, not
 * individual high-speed edges. Keeping this outside the IRQ preserves
 * the v1.3 capture timing and the 50 kHz duty filtering behavior. */
static void pulse_stats_reset(LabMateApp* app) {
    app->pulse_stats_valid = false;
    app->pulse_stats_last_valid = false;
    app->pulse_stats_last_high_cycles = 0U;
    app->pulse_stats_last_low_cycles = 0U;
    app->pulse_min_high_cycles = 0U;
    app->pulse_max_high_cycles = 0U;
    app->pulse_min_low_cycles = 0U;
    app->pulse_max_low_cycles = 0U;
    app->pulse_min_period_cycles = 0U;
    app->pulse_max_period_cycles = 0U;
    app->pulse_min_duty_permille = 0U;
    app->pulse_max_duty_permille = 0U;
}

static void pulse_stats_record(LabMateApp* app) {
    if(!app->pulse_period_valid) return;

    const uint32_t high = app->pulse_high_cycles;
    const uint32_t low = app->pulse_low_cycles;

    /* A 10 ms redraw must not count an unchanged IRQ snapshot again. */
    if(app->pulse_stats_last_valid &&
       high == app->pulse_stats_last_high_cycles &&
       low == app->pulse_stats_last_low_cycles) {
        return;
    }

    app->pulse_stats_last_high_cycles = high;
    app->pulse_stats_last_low_cycles = low;
    app->pulse_stats_last_valid = true;

    const uint32_t period = app->pulse_period_cycles;
    const uint32_t duty = app->pulse_duty_permille;

    if(!app->pulse_stats_valid) {
        app->pulse_min_high_cycles = high;
        app->pulse_max_high_cycles = high;
        app->pulse_min_low_cycles = low;
        app->pulse_max_low_cycles = low;
        app->pulse_min_period_cycles = period;
        app->pulse_max_period_cycles = period;
        app->pulse_min_duty_permille = duty;
        app->pulse_max_duty_permille = duty;
        app->pulse_stats_valid = true;
        return;
    }

    if(high < app->pulse_min_high_cycles) app->pulse_min_high_cycles = high;
    if(high > app->pulse_max_high_cycles) app->pulse_max_high_cycles = high;
    if(low < app->pulse_min_low_cycles) app->pulse_min_low_cycles = low;
    if(low > app->pulse_max_low_cycles) app->pulse_max_low_cycles = low;
    if(period < app->pulse_min_period_cycles) app->pulse_min_period_cycles = period;
    if(period > app->pulse_max_period_cycles) app->pulse_max_period_cycles = period;
    if(duty < app->pulse_min_duty_permille) app->pulse_min_duty_permille = duty;
    if(duty > app->pulse_max_duty_permille) app->pulse_max_duty_permille = duty;
}

/*
 * Pulse Analyzer v1.3: presentation-only formatter.
 * Keep the IRQ capture and the measurement calculations untouched.
 * Use short values that fit within a 60-pixel metric column.
 */
static void pulse_ui_format_value(char* text, size_t size, uint32_t cycles) {
    const uint64_t us = pulse_cycles_to_us(cycles);

    if(us < 1000ULL) {
        snprintf(text, size, "%luus", (unsigned long)us);
    } else if(us < 10000ULL) {
        snprintf(text, size, "%lu.%02lums",
                 (unsigned long)(us / 1000ULL),
                 (unsigned long)((us % 1000ULL) / 10ULL));
    } else if(us < 10000000ULL) {
        snprintf(text, size, "%lums", (unsigned long)((us + 500ULL) / 1000ULL));
    } else {
        snprintf(text, size, "%lus", (unsigned long)((us + 500000ULL) / 1000000ULL));
    }
}

static void measurement_update(LabMateApp* app) {
    if(app->hold) return;

    uint32_t now = furi_get_tick();
    uint32_t tick_frequency =
        furi_kernel_get_tick_frequency();

    /*
     * FREQUENCY METER
     *
     * Rising edges are captured by the GPIO interrupt.
     * The main loop only consumes the period measured
     * by the ISR and performs filtering/calculation.
     */
    if(app->screen == LabMateScreenFrequency) {

        /*
         * High-frequency hardware counter mode.
         * PB3 / TIM2_CH2 counts edges without GPIO interrupts.
         */
        if(app->frequency_hw_active) {
            uint32_t current_cycle = DWT->CYCCNT;
            uint32_t elapsed_cycles =
                current_cycle -
                app->frequency_hw_last_cycle;

            /*
             * Update roughly every 100 ms.
             */
            if(SystemCoreClock > 0 &&
               elapsed_cycles >=
                   (SystemCoreClock / 10U)) {

                uint32_t current_count =
                    LL_TIM_GetCounter(TIM2);

                uint32_t delta_count =
                    current_count -
                    app->frequency_hw_last_count;

                app->frequency_hw_last_count =
                    current_count;

                app->frequency_hw_last_cycle =
                    current_cycle;

                app->edges = current_count;

                if(delta_count > 0) {
                    app->frequency_millihz =
                        (uint32_t)(
                            (((uint64_t)delta_count *
                              (uint64_t)SystemCoreClock *
                              1000ULL) +
                             (elapsed_cycles / 2U)) /
                            elapsed_cycles);

                    app->frequency_valid = true;
                    app->frequency_last_edge = now;
                    frequency_stats_record(app);

                } else if(
                    tick_frequency > 0 &&
                    (now -
                     app->frequency_last_edge) >
                        (tick_frequency * 3U)) {

                    app->frequency_millihz = 0;
                    app->frequency_valid = false;
                }
            }

            return;
        }

        if(app->frequency_irq_new_period) {

            uint32_t period_cycles;

            /*
             * Copy the volatile ISR value first, then
             * acknowledge it.
             */
            period_cycles =
                app->frequency_irq_period_cycles;

            app->frequency_irq_new_period = false;

            if(period_cycles > 0 &&
               SystemCoreClock > 0) {

                app->frequency_period_samples[
                    app->frequency_sample_index] =
                    period_cycles;

                app->frequency_sample_index =
                    (app->frequency_sample_index + 1U) %
                    8U;

                if(app->frequency_sample_count < 8U) {
                    app->frequency_sample_count++;
                }

                uint64_t period_sum = 0;
                uint32_t period_min = UINT32_MAX;
                uint32_t period_max = 0;

                for(uint8_t s = 0;
                    s < app->frequency_sample_count;
                    s++) {

                    uint32_t sample =
                        app->frequency_period_samples[s];

                    period_sum += sample;

                    if(sample < period_min) {
                        period_min = sample;
                    }

                    if(sample > period_max) {
                        period_max = sample;
                    }
                }

                uint8_t averaging_count =
                    app->frequency_sample_count;

                /*
                 * Trim one minimum and one maximum sample
                 * once enough measurements are available.
                 */
                if(averaging_count >= 5U) {
                    period_sum -= period_min;
                    period_sum -= period_max;
                    averaging_count -= 2U;
                }

                uint32_t average_period =
                    (uint32_t)(
                        (period_sum +
                         (averaging_count / 2U)) /
                        averaging_count);

                if(average_period > 0) {

                    app->frequency_period_ticks =
                        average_period;

                    app->frequency_millihz =
                        (uint32_t)(
                            (((uint64_t)SystemCoreClock *
                              1000ULL) +
                             (average_period / 2U)) /
                            average_period);

                    app->frequency_valid = true;
                    frequency_stats_record(app);
                }
            }
        }

        /*
         * Keep the displayed edge counter connected
         * to the real interrupt counter.
         */
        app->edges =
            app->frequency_irq_edges;

        /*
         * No rising edge for 3 seconds -> signal lost.
         */
        if(app->frequency_irq_last_tick != 0 &&
           tick_frequency > 0) {

            uint32_t no_edge_ticks =
                now -
                app->frequency_irq_last_tick;

            if(no_edge_ticks >
               (tick_frequency * 3U)) {

                app->frequency_millihz = 0;
                app->frequency_valid = false;

                app->frequency_sample_index = 0;
                app->frequency_sample_count = 0;

                app->frequency_irq_last_cycle = 0;
                app->frequency_irq_cycle_accumulator = 0;
                app->frequency_irq_accumulated_periods = 0;

                memset(
                    app->frequency_period_samples,
                    0,
                    sizeof(
                        app->frequency_period_samples));
            }
        }

        return;
    }

    /* PULSE ANALYZER: copy one coherent IRQ snapshot. */
    if(app->screen == LabMateScreenPulse) {
        uint32_t hi, lo, last_tick, count;
        bool hi_valid, lo_valid;

        FURI_CRITICAL_ENTER();
        hi = app->pulse_irq_high_cycles;
        lo = app->pulse_irq_low_cycles;
        hi_valid = app->pulse_irq_high_valid;
        lo_valid = app->pulse_irq_low_valid;
        last_tick = app->pulse_irq_last_tick;
        count = app->pulse_irq_edges;
        FURI_CRITICAL_EXIT();

        /* A disconnected or stopped source must not display stale data.
         * Restart synchronization after a long quiet interval.
         */
        if(tick_frequency > 0U &&
           (now - last_tick) > (tick_frequency * 3U)) {
            FURI_CRITICAL_ENTER();
            app->pulse_irq_seen = false;
            app->pulse_irq_high_valid = false;
            app->pulse_irq_low_valid = false;
            app->pulse_irq_high_sum = 0;
            app->pulse_irq_low_sum = 0;
            app->pulse_irq_high_samples = 0;
            app->pulse_irq_low_samples = 0;
            app->pulse_irq_wide_window = false;
            app->pulse_irq_last_tick = now;
            FURI_CRITICAL_EXIT();
            hi_valid = false;
            lo_valid = false;
        }

        app->edges = count;
        app->pulse_high_valid = hi_valid;
        app->pulse_low_valid = lo_valid;
        app->pulse_high_cycles = hi;
        app->pulse_low_cycles = lo;
        pulse_recalculate(app);
        pulse_stats_record(app);
        return;
    }

    /* GPIO Monitor retains its simple state/edge polling path. */
    bool current = furi_hal_gpio_read(labmate_gpio_pins[app->gpio_index]);
    if(current != app->gpio_previous_state) {
        app->edges++;
        app->gpio_previous_state = current;
    }
    app->gpio_state = current;
}

/* ---------- SIGNAL GENERATOR ---------- */

static void generator_stop(LabMateApp* app) {
    if(app->generator_running) {
        furi_hal_pwm_stop(
            FuriHalPwmOutputIdTim1PA7);
    }

    app->generator_running = false;
    app->generator_state = false;
}

static void generator_start(LabMateApp* app) {
    uint32_t freq =
        generator_frequencies[
            app->generator_freq_index];

    if(freq == 0) {
        return;
    }

    /*
     * Hardware PWM on PA7 / TIM1.
     * No per-edge generator ISR is required.
     */
    furi_hal_pwm_start(
        FuriHalPwmOutputIdTim1PA7,
        freq,
        50U);

    app->generator_running = true;
    app->generator_state = false;
}
static void generator_change_frequency(
    LabMateApp* app,
    int8_t direction) {

    if(direction > 0) {
        app->generator_freq_index++;

        if(app->generator_freq_index >=
           GENERATOR_FREQ_COUNT) {

            app->generator_freq_index = 0;
        }
    } else {
        if(app->generator_freq_index == 0) {
            app->generator_freq_index =
                GENERATOR_FREQ_COUNT - 1;
        } else {
            app->generator_freq_index--;
        }
    }

    /*
     * Update TIM1 PWM parameters in place while running.
     * Do not stop and re-enable TIM1 for each key press.
     * This keeps PA7 configured and avoids repeated timer/bus resets.
     */
    if(app->generator_running) {
        furi_hal_pwm_set_params(
            FuriHalPwmOutputIdTim1PA7,
            generator_frequencies[app->generator_freq_index],
            50U);
    }
}

/* ---------- DRAWING ---------- */

static void ui_badge(
    Canvas* canvas,
    uint8_t x,
    uint8_t y,
    uint8_t w,
    const char* text,
    bool filled) {

    if(filled) {
        canvas_draw_box(canvas, x, y, w, 11);
        canvas_set_color(canvas, ColorWhite);
    } else {
        canvas_draw_frame(canvas, x, y, w, 11);
    }

    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, x + 4, y + 8, text);

    if(filled) {
        canvas_set_color(canvas, ColorBlack);
    }
}

static void ui_key(
    Canvas* canvas,
    uint8_t x,
    const char* key,
    const char* label) {

    canvas_draw_frame(canvas, x, 53, 18, 10);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, x + 3, 61, key);
    canvas_draw_str(canvas, x + 21, 61, label);
}

static void ui_icon_gpio(
    Canvas* canvas,
    uint8_t x,
    uint8_t y) {

    canvas_draw_frame(canvas, x + 2, y + 2, 8, 8);

    canvas_draw_line(canvas, x, y + 4, x + 2, y + 4);
    canvas_draw_line(canvas, x, y + 7, x + 2, y + 7);

    canvas_draw_line(canvas, x + 10, y + 4, x + 12, y + 4);
    canvas_draw_line(canvas, x + 10, y + 7, x + 12, y + 7);
}

static void ui_icon_frequency(
    Canvas* canvas,
    uint8_t x,
    uint8_t y) {

    canvas_draw_line(canvas, x, y + 7, x + 2, y + 7);
    canvas_draw_line(canvas, x + 2, y + 7, x + 4, y + 3);
    canvas_draw_line(canvas, x + 4, y + 3, x + 6, y + 9);
    canvas_draw_line(canvas, x + 6, y + 9, x + 8, y + 4);
    canvas_draw_line(canvas, x + 8, y + 4, x + 11, y + 4);
}

static void ui_icon_pulse(
    Canvas* canvas,
    uint8_t x,
    uint8_t y) {

    canvas_draw_line(canvas, x, y + 8, x + 3, y + 8);
    canvas_draw_line(canvas, x + 3, y + 8, x + 3, y + 3);
    canvas_draw_line(canvas, x + 3, y + 3, x + 7, y + 3);
    canvas_draw_line(canvas, x + 7, y + 3, x + 7, y + 8);
    canvas_draw_line(canvas, x + 7, y + 8, x + 11, y + 8);
}

static void ui_icon_generator(
    Canvas* canvas,
    uint8_t x,
    uint8_t y) {

    canvas_draw_line(canvas, x + 5, y, x + 2, y + 6);
    canvas_draw_line(canvas, x + 2, y + 6, x + 6, y + 6);
    canvas_draw_line(canvas, x + 6, y + 6, x + 4, y + 11);
    canvas_draw_line(canvas, x + 4, y + 11, x + 10, y + 4);
    canvas_draw_line(canvas, x + 10, y + 4, x + 6, y + 4);
}

static void ui_icon_info(
    Canvas* canvas,
    uint8_t x,
    uint8_t y) {

    canvas_draw_frame(canvas, x + 1, y + 1, 10, 10);
    canvas_draw_box(canvas, x + 5, y + 3, 2, 2);
    canvas_draw_line(canvas, x + 6, y + 6, x + 6, y + 9);
}

static void ui_draw_menu_icon(
    Canvas* canvas,
    uint8_t item,
    uint8_t x,
    uint8_t y) {

    switch(item) {
    case 0:
        ui_icon_gpio(canvas, x, y);
        break;
    case 1:
        ui_icon_frequency(canvas, x, y);
        break;
    case 2:
        ui_icon_pulse(canvas, x, y);
        break;
    case 3:
        ui_icon_generator(canvas, x, y);
        break;
    case 4:
        ui_icon_info(canvas, x, y);
        break;
    }
}

static void draw_header(
    Canvas* canvas,
    const char* title) {

    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 2, 10, title);

    canvas_draw_line(canvas, 0, 13, 127, 13);
}

static void draw_menu(
    Canvas* canvas,
    LabMateApp* app) {

    /*
     * LabMate v1.2 instrument-style main menu.
     */

    canvas_set_font(
        canvas,
        FontPrimary);

    canvas_draw_str(
        canvas,
        2,
        10,
        "LABMATE");

    /*
     * Version badge.
     */
    ui_badge(
        canvas,
        99,
        1,
        27,
        "v1.4d",
        false);

    canvas_draw_line(
        canvas,
        0,
        13,
        127,
        13);

    /*
     * Three visible rows.
     * Selected item remains centered where possible.
     */
    uint8_t first = 0;

    if(app->selected > 1) {
        first =
            app->selected - 1;
    }

    if(first + 3 > MENU_COUNT) {
        first =
            MENU_COUNT - 3;
    }

    for(uint8_t row = 0;
        row < 3;
        row++) {

        uint8_t i =
            first + row;

        uint8_t y =
            25 + (row * 12);

        if(i == app->selected) {

            /*
             * Inverted active row.
             */
            canvas_draw_box(
                canvas,
                1,
                y - 10,
                126,
                12);

            canvas_set_color(
                canvas,
                ColorWhite);

            ui_draw_menu_icon(
                canvas,
                i,
                4,
                y - 9);

            canvas_set_font(
                canvas,
                FontSecondary);

            canvas_draw_str(
                canvas,
                20,
                y,
                menu_items[i]);

            canvas_draw_str(
                canvas,
                117,
                y,
                ">");

            canvas_set_color(
                canvas,
                ColorBlack);

        } else {

            ui_draw_menu_icon(
                canvas,
                i,
                4,
                y - 9);

            canvas_set_font(
                canvas,
                FontSecondary);

            canvas_draw_str(
                canvas,
                20,
                y,
                menu_items[i]);

            canvas_draw_str(
                canvas,
                117,
                y,
                ">");
        }
    }

    canvas_draw_line(
        canvas,
        0,
        52,
        127,
        52);

    /*
     * Instrument-style navigation footer.
     */
    ui_key(
        canvas,
        2,
        "^v",
        "MOVE");

    ui_key(
        canvas,
        70,
        "OK",
        "OPEN");
}

static void draw_gpio(Canvas* canvas, LabMateApp* app) {
    char edges_text[32];
    const uint32_t edges = app->edges;

    /* Compact instrument header, consistent with Frequency and Pulse screens. */
    draw_header(canvas, "GPIO");
    ui_badge(canvas, 35, 1, 34, gpio_names[app->gpio_index], false);
    ui_badge(canvas, 91, 1, 35, app->hold ? "HOLD" : "LIVE", !app->hold);

    /* Separate the live logic level from the transition counter. */
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 4, 24, "LEVEL");
    canvas_draw_str(canvas, 70, 24, "EDGES");
    canvas_draw_line(canvas, 64, 18, 64, 50);

    /* Invert the level field only when HIGH; LOW remains outlined. */
    if(app->gpio_state) {
        canvas_draw_box(canvas, 2, 28, 58, 22);
        canvas_set_color(canvas, ColorWhite);
    } else {
        canvas_draw_frame(canvas, 2, 28, 58, 22);
    }
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, app->gpio_state ? 16 : 20, 44,
                    app->gpio_state ? "HIGH" : "LOW");
    if(app->gpio_state) canvas_set_color(canvas, ColorBlack);

    /* Keep large edge counts inside the 58-pixel value column. */
    if(edges >= 1000000U) {
        snprintf(edges_text, sizeof(edges_text), "%lu.%luM",
                 (unsigned long)(edges / 1000000U),
                 (unsigned long)((edges % 1000000U) / 100000U));
    } else if(edges >= 10000U) {
        snprintf(edges_text, sizeof(edges_text), "%lu.%luk",
                 (unsigned long)(edges / 1000U),
                 (unsigned long)((edges % 1000U) / 100U));
    } else {
        snprintf(edges_text, sizeof(edges_text), "%lu", (unsigned long)edges);
    }
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 70, 41, edges_text);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 70, 49, "POLL");

    canvas_draw_line(canvas, 0, 52, 127, 52);
    ui_key(canvas, 2, "<>", "PIN");
    ui_key(canvas, 70, "OK", app->hold ? "LIVE" : "HOLD");
}

/* Compact MIN/MAX display in two fixed-width cells.
 * Use the SAME truncation policy as the main frequency reading:
 * e.g. an actual 49.996 kHz displays as 49.99 kHz above and 49.99k
 * in MIN/MAX, rather than incorrectly appearing as 50.00k below.
 * Never switch units before the true 1 kHz / 10 kHz / 100 kHz boundary.
 * The stored millihertz measurements and recording logic are unchanged.
 */
static void frequency_format_compact(char* text, size_t size, uint32_t mhz, bool valid) {
    if(!valid) {
        snprintf(text, size, "---");
        return;
    }

    if(mhz >= 1000000000U) {
        /* 1.00 MHz and above. */
        uint32_t v = mhz / 10000000U;
        snprintf(text, size, "%lu.%02luM", (unsigned long)(v / 100U),
                 (unsigned long)(v % 100U));
    } else if(mhz >= 100000000U) {
        /* 100.0 kHz .. 999.9 kHz. */
        uint32_t v = mhz / 100000U;
        snprintf(text, size, "%lu.%01luk", (unsigned long)(v / 10U),
                 (unsigned long)(v % 10U));
    } else if(mhz >= 10000000U) {
        /* 10.00 kHz .. 99.99 kHz: same 10 Hz steps as the main reading. */
        uint32_t v = mhz / 10000U;
        snprintf(text, size, "%lu.%02luk", (unsigned long)(v / 100U),
                 (unsigned long)(v % 100U));
    } else if(mhz >= 1000000U) {
        /* 1.000 kHz .. 9.999 kHz. */
        uint32_t v = mhz / 1000U;
        snprintf(text, size, "%lu.%03luk", (unsigned long)(v / 1000U),
                 (unsigned long)(v % 1000U));
    } else if(mhz >= 10000U) {
        /* 10.0 .. 999.9 Hz; never round 999.9 Hz up to 1 kHz. */
        uint32_t v = mhz / 100U;
        snprintf(text, size, "%lu.%01luHz", (unsigned long)(v / 10U),
                 (unsigned long)(v % 10U));
    } else {
        /* 0.00 .. 9.99 Hz. */
        uint32_t v = mhz / 10U;
        snprintf(text, size, "%lu.%02luHz", (unsigned long)(v / 100U),
                 (unsigned long)(v % 100U));
    }
}

/* Edge count is intentionally abbreviated to retain an on-screen indicator. */
static void frequency_format_edges(char* text, size_t size, uint32_t edges) {
    if(edges >= 1000000U) {
        snprintf(text, size, "E:%luM", (unsigned long)(edges / 1000000U));
    } else if(edges >= 10000U) {
        snprintf(text, size, "E:%luk", (unsigned long)(edges / 1000U));
    } else {
        snprintf(text, size, "E:%lu", (unsigned long)edges);
    }
}

static void draw_frequency(Canvas* canvas, LabMateApp* app) {
    char value[32];
    char edges_label[20];
    char min_value[20];
    char max_value[20];
    const bool high_mode = app->gpio_index == 4U;

    /* Compact status bar, matching the Pulse Analyzer layout. */
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 2, 10, "FREQ");
    ui_badge(canvas, 34, 1, 55, high_mode ? "HIGH PB3" : "LOW PC1", false);
    ui_badge(canvas, 91, 1, 35, app->hold ? "HOLD" : "LIVE", !app->hold);
    canvas_draw_line(canvas, 0, 13, 127, 13);

    if(app->frequency_valid) {
        uint32_t hz = app->frequency_millihz / 1000U;
        uint32_t decimal = (app->frequency_millihz % 1000U) / 10U;

        if(hz >= 1000U) {
            /* Keep the existing measured frequency formatting unchanged. */
            uint32_t khz_whole = hz / 1000U;
            uint32_t khz_decimal = (hz % 1000U) / 10U;
            snprintf(value, sizeof(value), "%lu.%02lu kHz",
                     (unsigned long)khz_whole,
                     (unsigned long)khz_decimal);
        } else {
            snprintf(value, sizeof(value), "%lu.%02lu Hz",
                     (unsigned long)hz,
                     (unsigned long)decimal);
        }
    } else {
        snprintf(value, sizeof(value), "--- Hz");
    }

    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 3, 24, "FREQUENCY");
    frequency_format_edges(edges_label, sizeof(edges_label), app->edges);
    canvas_draw_str(canvas, 83, 24, edges_label);

    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 4, 38, value);

    frequency_format_compact(min_value, sizeof(min_value),
        app->frequency_min_millihz, app->frequency_stats_valid);
    frequency_format_compact(max_value, sizeof(max_value),
        app->frequency_max_millihz, app->frequency_stats_valid);
    canvas_set_font(canvas, FontSecondary);
    /* Two fixed-width cells: MIN 0..64, MAX 66..127.
     * Seven 6px FontSecondary characters fit within each value area. */
    canvas_draw_str(canvas, 2, 49, "MIN");
    canvas_draw_str(canvas, 22, 49, min_value);
    canvas_draw_str(canvas, 66, 49, "MAX");
    /* Right-align the value to leave a readable gap after MAX without clipping. */
    canvas_draw_str_aligned(canvas, 127, 49, AlignRight, AlignBottom, max_value);

    /* Keep the three action hints separate at 128x64 resolution. */
    canvas_draw_line(canvas, 0, 52, 127, 52);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 2, 61, "<> MODE");
    canvas_draw_str(canvas, 49, 61, app->hold ? "OK LIVE" : "OK HOLD");
    canvas_draw_str(canvas, 102, 61, "^RST");
}

static void pulse_ui_metric(
    Canvas* canvas,
    uint8_t x,
    uint8_t label_y,
    uint8_t value_y,
    const char* label,
    const char* value) {

    /* Both labels and values use the compact 6x8 font. The large
     * FontPrimary glyphs extend upwards into the label row inside
     * the LCD's 18-pixel metric cells, hiding parts of both strings. */
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, x, label_y, label);
    canvas_draw_str(canvas, x, value_y, value);
}

/* Second Pulse Analyzer page: four rows, MIN and MAX columns.
 * The 128x64 LCD cannot show twelve detailed values in the LIVE grid.
 * Keep the existing live 2x2 display untouched. */
static void draw_pulse_stats(Canvas* canvas, LabMateApp* app) {
    char hi_min[24] = "---";
    char hi_max[24] = "---";
    char lo_min[24] = "---";
    char lo_max[24] = "---";
    char per_min[24] = "---";
    char per_max[24] = "---";
    char duty_min[24] = "---";
    char duty_max[24] = "---";

    if(app->pulse_stats_valid) {
        pulse_ui_format_value(hi_min, sizeof(hi_min), app->pulse_min_high_cycles);
        pulse_ui_format_value(hi_max, sizeof(hi_max), app->pulse_max_high_cycles);
        pulse_ui_format_value(lo_min, sizeof(lo_min), app->pulse_min_low_cycles);
        pulse_ui_format_value(lo_max, sizeof(lo_max), app->pulse_max_low_cycles);
        pulse_ui_format_value(per_min, sizeof(per_min), app->pulse_min_period_cycles);
        pulse_ui_format_value(per_max, sizeof(per_max), app->pulse_max_period_cycles);
        snprintf(duty_min, sizeof(duty_min), "%lu.%lu%%",
                 (unsigned long)(app->pulse_min_duty_permille / 10U),
                 (unsigned long)(app->pulse_min_duty_permille % 10U));
        snprintf(duty_max, sizeof(duty_max), "%lu.%lu%%",
                 (unsigned long)(app->pulse_max_duty_permille / 10U),
                 (unsigned long)(app->pulse_max_duty_permille % 10U));
    }

    canvas_set_font(canvas, FontSecondary);
    /* Fixed table cells leave room for seven-character values in each
     * numeric column. The row baselines are >= 8px apart. */
    canvas_draw_str(canvas, 3, 21, "TYPE");
    canvas_draw_str(canvas, 42, 21, "MIN");
    canvas_draw_str(canvas, 87, 21, "MAX");
    canvas_draw_line(canvas, 0, 23, 127, 23);

    canvas_draw_str(canvas, 3, 31, "HIGH");
    canvas_draw_str(canvas, 40, 31, hi_min);
    canvas_draw_str(canvas, 85, 31, hi_max);

    canvas_draw_str(canvas, 3, 39, "LOW");
    canvas_draw_str(canvas, 40, 39, lo_min);
    canvas_draw_str(canvas, 85, 39, lo_max);

    canvas_draw_str(canvas, 3, 47, "PER");
    canvas_draw_str(canvas, 40, 47, per_min);
    canvas_draw_str(canvas, 85, 47, per_max);

    canvas_draw_str(canvas, 3, 54, "DUTY");
    canvas_draw_str(canvas, 40, 54, duty_min);
    canvas_draw_str(canvas, 85, 54, duty_max);

    /* Short footer labels fit across all 128 pixels; avoid text
     * beyond x=127 and a baseline on the bottommost pixel. */
    canvas_draw_line(canvas, 0, 56, 127, 56);
    canvas_draw_str(canvas, 3, 62, "vRST");
    canvas_draw_str(canvas, 45, 62, app->hold ? "OK LIVE" : "OK HOLD");
    canvas_draw_str(canvas, 95, 62, "^BACK");
}

static void draw_pulse(Canvas* canvas, LabMateApp* app) {
    char high[24] = "---";
    char low[24] = "---";
    char period[24] = "---";
    char duty[24] = "---";

    /* Compact instrument header with input and capture state. */
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 2, 10, "PULSE");
    ui_badge(canvas, 56, 1, 33, gpio_names[app->gpio_index], false);
    ui_badge(canvas, 91, 1, 35, app->hold ? "HOLD" : "LIVE", !app->hold);
    canvas_draw_line(canvas, 0, 13, 127, 13);

    if(app->pulse_stats_view) {
        draw_pulse_stats(canvas, app);
        return;
    }

    if(app->pulse_high_valid) {
        pulse_ui_format_value(high, sizeof(high), app->pulse_high_cycles);
    }
    if(app->pulse_low_valid) {
        pulse_ui_format_value(low, sizeof(low), app->pulse_low_cycles);
    }
    if(app->pulse_period_valid) {
        pulse_ui_format_value(period, sizeof(period), app->pulse_period_cycles);
        snprintf(duty, sizeof(duty), "%lu.%lu%%",
                 (unsigned long)(app->pulse_duty_permille / 10U),
                 (unsigned long)(app->pulse_duty_permille % 10U));
    }

    /* 2 x 2 measurement grid.
     * Use separate baselines for text and separators: on the 128x64
     * display, even a one-pixel collision cuts the labels visibly.
     * The measurement values and IRQ engine are unchanged.
     */
    canvas_draw_line(canvas, 64, 15, 64, 51);
    canvas_draw_line(canvas, 2, 33, 126, 33);
    pulse_ui_metric(canvas, 3, 21, 31, "HIGH", high);
    pulse_ui_metric(canvas, 68, 21, 31, "LOW", low);
    pulse_ui_metric(canvas, 3, 41, 50, "PERIOD", period);
    pulse_ui_metric(canvas, 68, 41, 50, "DUTY", duty);

    /* Navigation: short captions fit the actual 128px viewport. */
    canvas_draw_line(canvas, 0, 52, 127, 52);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 3, 61, "<>PIN");
    canvas_draw_str(canvas, 45, 61, app->hold ? "OK LIVE" : "OK HOLD");
    canvas_draw_str(canvas, 96, 61, "^STAT");
}

static void draw_generator(Canvas* canvas, LabMateApp* app) {
    char value[32];
    const uint32_t freq = generator_frequencies[app->generator_freq_index];

    /* Output and RUN/STOP are visible even when switching presets. */
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 2, 10, "GEN");
    ui_badge(canvas, 34, 1, 55, "OUT PA7", false);
    ui_badge(canvas, 91, 1, 35, app->generator_running ? "RUN" : "STOP",
             app->generator_running);
    canvas_draw_line(canvas, 0, 13, 127, 13);

    /* Only the visual presentation changes: PWM remains TIM1/PA7. */
    if(freq >= 1000U && (freq % 1000U) == 0U) {
        snprintf(value, sizeof(value), "%lu kHz", (unsigned long)(freq / 1000U));
    } else {
        snprintf(value, sizeof(value), "%lu Hz", (unsigned long)freq);
    }

    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 3, 24, "OUTPUT FREQ");
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 4, 40, value);

    canvas_draw_line(canvas, 84, 17, 84, 50);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 90, 27, "DUTY");
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 90, 41, "50%");

    canvas_draw_line(canvas, 0, 52, 127, 52);
    ui_key(canvas, 2, "<>", "FREQ");
    ui_key(canvas, 70, "OK", app->generator_running ? "STOP" : "START");
}

static void draw_about(
    Canvas* canvas) {

    canvas_set_font(
        canvas,
        FontPrimary);

    canvas_draw_str(
        canvas,
        2,
        10,
        "LABMATE v1.4d");

    canvas_draw_line(
        canvas,
        0,
        13,
        127,
        13);

    canvas_set_font(
        canvas,
        FontSecondary);

    canvas_draw_str(
        canvas,
        2,
        24,
        "Digital Signal Toolkit");

    canvas_draw_str(
        canvas,
        2,
        36,
        "LOW PC1");

    canvas_draw_str(
        canvas,
        47,
        36,
        "HIGH PB3");

    canvas_draw_str(
        canvas,
        2,
        48,
        "GEN PA7");

    canvas_draw_str(
        canvas,
        2,
        60,
        "3.3V GPIO ONLY");
}
static void render_callback(
    Canvas* canvas,
    void* ctx) {

    LabMateApp* app = ctx;

    furi_mutex_acquire(
        app->mutex,
        FuriWaitForever);

    canvas_clear(canvas);

    switch(app->screen) {
    case LabMateScreenMenu:
        draw_menu(canvas, app);
        break;

    case LabMateScreenGpio:
        draw_gpio(canvas, app);
        break;

    case LabMateScreenFrequency:
        draw_frequency(canvas, app);
        break;

    case LabMateScreenPulse:
        draw_pulse(canvas, app);
        break;

    case LabMateScreenGenerator:
        draw_generator(canvas, app);
        break;

    case LabMateScreenAbout:
        draw_about(canvas);
        break;
    }

    furi_mutex_release(
        app->mutex);
}

static void input_callback(
    InputEvent* input_event,
    void* ctx) {

    FuriMessageQueue* queue =
        ctx;

    furi_message_queue_put(
        queue,
        input_event,
        0);
}

static bool screen_uses_gpio(
    LabMateScreen screen) {

    return
        screen == LabMateScreenGpio ||
        screen == LabMateScreenFrequency ||
        screen == LabMateScreenPulse;
}

int32_t labmate_app(void* p) {
    UNUSED(p);

    LabMateApp* app =
        malloc(sizeof(LabMateApp));

    if(!app) {
        return -1;
    }

    memset(
        app,
        0,
        sizeof(LabMateApp));

    app->running = true;
    app->hold = false;
    app->selected = 0;
    app->gpio_index = 1; /* PC1 */
    app->generator_freq_index = 0; /* 1 Hz */
    app->screen = LabMateScreenMenu;

    app->mutex =
        furi_mutex_alloc(
            FuriMutexTypeNormal);

    if(!app->mutex) {
        free(app);
        return -1;
    }

    FuriMessageQueue* queue =
        furi_message_queue_alloc(
            16,
            sizeof(InputEvent));

    if(!queue) {
        furi_mutex_free(app->mutex);
        free(app);
        return -1;
    }

    ViewPort* viewport =
        view_port_alloc();

    if(!viewport) {
        furi_message_queue_free(queue);
        furi_mutex_free(app->mutex);
        free(app);
        return -1;
    }

    view_port_draw_callback_set(
        viewport,
        render_callback,
        app);

    view_port_input_callback_set(
        viewport,
        input_callback,
        queue);

    Gui* gui =
        furi_record_open(
            RECORD_GUI);

    gui_add_view_port(
        gui,
        viewport,
        GuiLayerFullscreen);

    InputEvent event;

    /* GUI refresh is 10 Hz normally, 5 Hz from 8 kHz upward.
     * Measurement remains interrupt-driven at every signal edge.
     */
    uint32_t pulse_redraw_interval = furi_kernel_get_tick_frequency() / 10U;
    uint32_t pulse_busy_redraw_interval = furi_kernel_get_tick_frequency() / 5U;
    if(pulse_redraw_interval == 0U) pulse_redraw_interval = 1U;
    if(pulse_busy_redraw_interval == 0U) pulse_busy_redraw_interval = 1U;
    const uint32_t pulse_fast_period_cycles = SystemCoreClock / 8000U;
    uint32_t pulse_redraw_last_tick = furi_get_tick();

    /* Diagnostic v1.4: avoid unnecessary 100 Hz repaint of the main menu
     * while attached to the USB host. Keys still trigger an immediate redraw.
     * Pulse Analyzer retains its separately throttled redraw policy. */
    uint32_t normal_redraw_interval = furi_kernel_get_tick_frequency() / 10U;
    if(normal_redraw_interval == 0U) normal_redraw_interval = 1U;
    uint32_t normal_redraw_last_tick = furi_get_tick();

    while(app->running) {
        FuriStatus status =
            furi_message_queue_get(
                queue,
                &event,
                10);

        furi_mutex_acquire(
            app->mutex,
            FuriWaitForever);

        if(screen_uses_gpio(
               app->screen)) {
            measurement_update(app);
        }

        if(status == FuriStatusOk &&
           event.type == InputTypePress) {

            if(app->screen ==
               LabMateScreenMenu) {

                if(event.key == InputKeyUp) {
                    if(app->selected == 0) {
                        app->selected =
                            MENU_COUNT - 1;
                    } else {
                        app->selected--;
                    }

                } else if(
                    event.key == InputKeyDown) {

                    app->selected++;

                    if(app->selected >=
                       MENU_COUNT) {
                        app->selected = 0;
                    }

                } else if(
                    event.key == InputKeyOk) {

                    switch(app->selected) {
                    case 0:
                        app->screen =
                            LabMateScreenGpio;
                        app->hold = false;
                        gpio_activate(app);
                        break;

                    case 1:
                        app->screen =
                            LabMateScreenFrequency;
                        app->hold = false;

                        app->gpio_index = 4U; /* PB3 / HIGH mode */
                        frequency_stats_reset(app);
                        measurement_reset(app);
                        frequency_hw_start(app);
                        break;

                    case 2:
                        app->screen =
                            LabMateScreenPulse;
                        app->hold = false;
                        /* Previous tools may have left PB3/PC3 selected. */
                        app->gpio_index = 1U; /* PC1, a safe EXTI line */
                        app->pulse_stats_view = false;
                        pulse_stats_reset(app);
                        measurement_reset(app);
                        pulse_interrupt_start(app);
                        break;

                    case 3:
                        app->screen =
                            LabMateScreenGenerator;
                        break;

                    case 4:
                        app->screen =
                            LabMateScreenAbout;
                        break;
                    }

                } else if(
                    event.key == InputKeyBack) {
                    app->running = false;
                }

            } else if(
                screen_uses_gpio(
                    app->screen)) {

                if(app->screen == LabMateScreenFrequency &&
                   event.key == InputKeyUp) {
                    if(!app->hold) frequency_stats_reset(app);

                } else if(app->screen == LabMateScreenPulse &&
                          event.key == InputKeyUp) {
                    app->pulse_stats_view = !app->pulse_stats_view;

                } else if(app->screen == LabMateScreenPulse &&
                          event.key == InputKeyDown) {
                    if(!app->hold) pulse_stats_reset(app);

                } else if(event.key == InputKeyLeft) {
                    gpio_change(app, -1);

                } else if(
                    event.key == InputKeyRight) {
                    gpio_change(app, 1);

                } else if(
                    event.key == InputKeyOk) {

                    if(app->screen == LabMateScreenPulse) {
                        if(app->hold) {
                            /* Resume with a fresh IRQ capture window. */
                            measurement_reset(app);
                            pulse_interrupt_start(app);
                            app->hold = false;
                        } else {
                            /* Freeze displayed values and stop IRQ load. */
                            pulse_interrupt_stop(app);
                            app->hold = true;
                        }
                    } else {
                        app->hold = !app->hold;
                        if(!app->hold) {
                            app->gpio_state = furi_hal_gpio_read(
                                labmate_gpio_pins[app->gpio_index]);
                            app->gpio_previous_state = app->gpio_state;
                            measurement_reset(app);
                            if(app->screen == LabMateScreenFrequency &&
                               app->frequency_hw_active) {
                                app->frequency_hw_last_count = LL_TIM_GetCounter(TIM2);
                                app->frequency_hw_last_cycle = DWT->CYCCNT;
                            }
                        }
                    }

                } else if(
                    event.key == InputKeyBack) {

                    if(app->screen ==
                       LabMateScreenFrequency) {
                        frequency_hw_stop(app);
                        frequency_interrupt_stop(app);
                    } else if(app->screen == LabMateScreenPulse) {
                        pulse_interrupt_stop(app);
                    }

                    gpio_release(
                        app->gpio_index);

                    app->hold = false;
                    app->screen =
                        LabMateScreenMenu;
                }

            } else if(
                app->screen ==
                LabMateScreenGenerator) {

                if(event.key == InputKeyLeft) {
                    generator_change_frequency(
                        app,
                        -1);

                } else if(
                    event.key == InputKeyRight) {
                    generator_change_frequency(
                        app,
                        1);

                } else if(
                    event.key == InputKeyOk) {

                    if(app->generator_running) {
                        generator_stop(app);
                    } else {
                        generator_start(app);
                    }

                } else if(
                    event.key == InputKeyBack) {

                    /*
                     * Keep generator running in background.
                     * Use OK in Generator screen to stop it.
                     */
                    app->screen =
                        LabMateScreenMenu;
                }

            } else {
                if(event.key == InputKeyBack) {
                    app->screen =
                        LabMateScreenMenu;
                }
            }
        }

        furi_mutex_release(
            app->mutex);

        /* Under heavy IRQ load, use a calmer LCD refresh rate while
         * preserving immediate response to keys and all captured edges.
         */
        if(app->screen == LabMateScreenPulse) {
            uint32_t tick = furi_get_tick();
            bool key_press =
                (status == FuriStatusOk && event.type == InputTypePress);
            const uint32_t redraw_interval =
                (app->pulse_period_valid && pulse_fast_period_cycles > 0U &&
                 app->pulse_period_cycles <= pulse_fast_period_cycles)
                    ? pulse_busy_redraw_interval
                    : pulse_redraw_interval;
            if(key_press ||
               (uint32_t)(tick - pulse_redraw_last_tick) >= redraw_interval) {
                view_port_update(viewport);
                pulse_redraw_last_tick = tick;
            }
        } else {
            const uint32_t redraw_tick = furi_get_tick();
            if(status == FuriStatusOk ||
               (uint32_t)(redraw_tick - normal_redraw_last_tick) >= normal_redraw_interval) {
                view_port_update(viewport);
                normal_redraw_last_tick = redraw_tick;
            }
        }
    }

    if(app->generator_running) {
        generator_stop(app);
    }

    if(screen_uses_gpio(app->screen)) {
        if(app->screen == LabMateScreenPulse) {
            pulse_interrupt_stop(app);
        } else if(app->screen == LabMateScreenFrequency) {
            frequency_hw_stop(app);
            frequency_interrupt_stop(app);
        }
        gpio_release(app->gpio_index);
    }

    gui_remove_view_port(
        gui,
        viewport);

    view_port_free(
        viewport);

    furi_record_close(
        RECORD_GUI);

    furi_message_queue_free(
        queue);

    furi_mutex_free(
        app->mutex);

    free(app);

    return 0;
}
























































