#include <furi.h>
#include <furi_hal.h>
#include <furi_hal_resources.h>
#include <furi_hal_pwm.h>
#include <furi_hal_bus.h>
#include <stm32wbxx_ll_tim.h>
#include <stm32wbxx_ll_exti.h>
#include <gui/gui.h>
#include <input/input.h>
#include <storage/storage.h>
#include "labmate_ui_primitives.h"
#include "labmate_internal.h"
#include "labmate_ui_screens.h"

#define LOGGER_DIR "/ext/apps_data/labmate"
#define LOGGER_INTERVAL_MS 1000U
/* Flush buffered records every ten 1-second samples to limit data loss. */
#define LOGGER_SYNC_EVERY_ROWS 10U
#define LOGGER_HISTORY_READ_BYTES 256U


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
const uint32_t labmate_generator_frequencies[] = {
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
uint64_t pulse_cycles_to_us(uint32_t cycles) {
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

/* Keep running extrema across HOLD and signal loss, but discard an
 * incomplete smoothing window whenever the capture source restarts. */
static void pulse_stats_window_reset(LabMateApp* app) {
    app->pulse_stats_recent_count = 0U;
    app->pulse_stats_recent_next = 0U;
    app->pulse_stats_recent_tick = 0U;
}

/* A five-element insertion sort runs in the app thread (not the IRQ).
 * Median values are selected from genuine captured measurements; they
 * are not synthetic target values and the result is not clamped to 50%. */
static uint32_t pulse_stats_median5(const uint32_t values[PULSE_STATS_FILTER_SAMPLES]) {
    uint32_t sorted[PULSE_STATS_FILTER_SAMPLES];
    for(uint8_t i = 0U; i < PULSE_STATS_FILTER_SAMPLES; ++i) {
        uint32_t value = values[i];
        uint8_t j = i;
        while(j > 0U && sorted[j - 1U] > value) {
            sorted[j] = sorted[j - 1U];
            --j;
        }
        sorted[j] = value;
    }
    return sorted[PULSE_STATS_FILTER_SAMPLES / 2U];
}

/* The extrema summarize published/averaged HIGH+LOW readings, not
 * individual high-speed edges. Keeping this outside the IRQ preserves
 * the v1.3 capture timing and 50 kHz live duty filtering behavior. */
static void pulse_stats_reset(LabMateApp* app) {
    app->pulse_stats_valid = false;
    app->pulse_stats_last_valid = false;
    app->pulse_stats_last_high_cycles = 0U;
    app->pulse_stats_last_low_cycles = 0U;
    pulse_stats_window_reset(app);
    app->pulse_min_high_cycles = 0U;
    app->pulse_max_high_cycles = 0U;
    app->pulse_min_low_cycles = 0U;
    app->pulse_max_low_cycles = 0U;
    app->pulse_min_period_cycles = 0U;
    app->pulse_max_period_cycles = 0U;
    app->pulse_min_duty_permille = 0U;
    app->pulse_max_duty_permille = 0U;
}

static void pulse_stats_record(LabMateApp* app, uint32_t now) {
    if(!app->pulse_period_valid) return;

    uint32_t high = app->pulse_high_cycles;
    uint32_t low = app->pulse_low_cycles;
    uint32_t period = app->pulse_period_cycles;
    uint32_t duty = app->pulse_duty_permille;

    /* At 8 kHz and above, isolated IRQ timestamp jitter must not become
     * a permanent MIN/MAX. Accept one averaged snapshot every 100 ms,
     * then record the MEDIAN of five successive readings for each field.
     * Persistent real changes are retained after the short window fills.
     * At slower speeds preserve the existing unfiltered MIN/MAX. */
    const uint32_t fast_limit_cycles = SystemCoreClock / 8000U;
    const bool fast = fast_limit_cycles > 0U && period <= fast_limit_cycles;

    if(fast) {
        uint32_t interval = furi_kernel_get_tick_frequency() / 10U;
        if(interval == 0U) interval = 1U;

        if(app->pulse_stats_recent_count > 0U &&
           (uint32_t)(now - app->pulse_stats_recent_tick) < interval) {
            return;
        }

        app->pulse_stats_recent_tick = now;
        PulseStatsSample* entry =
            &app->pulse_stats_recent[app->pulse_stats_recent_next];
        entry->high_cycles = high;
        entry->low_cycles = low;
        entry->period_cycles = period;
        entry->duty_permille = duty;

        app->pulse_stats_recent_next =
            (uint8_t)((app->pulse_stats_recent_next + 1U) %
                      PULSE_STATS_FILTER_SAMPLES);
        if(app->pulse_stats_recent_count < PULSE_STATS_FILTER_SAMPLES) {
            ++app->pulse_stats_recent_count;
        }
        if(app->pulse_stats_recent_count < PULSE_STATS_FILTER_SAMPLES) return;

        uint32_t highs[PULSE_STATS_FILTER_SAMPLES];
        uint32_t lows[PULSE_STATS_FILTER_SAMPLES];
        uint32_t periods[PULSE_STATS_FILTER_SAMPLES];
        uint32_t duties[PULSE_STATS_FILTER_SAMPLES];
        for(uint8_t i = 0U; i < PULSE_STATS_FILTER_SAMPLES; ++i) {
            const PulseStatsSample* sample = &app->pulse_stats_recent[i];
            highs[i] = sample->high_cycles;
            lows[i] = sample->low_cycles;
            periods[i] = sample->period_cycles;
            duties[i] = sample->duty_permille;
        }
        high = pulse_stats_median5(highs);
        low = pulse_stats_median5(lows);
        period = pulse_stats_median5(periods);
        duty = pulse_stats_median5(duties);
    } else {
        /* A slow reading is already an averaged capture and remains exact.
         * Do not mix slow measurements into the fast 5-sample window. */
        pulse_stats_window_reset(app);

        /* Polling without new IRQ results must not duplicate samples. */
        if(app->pulse_stats_last_valid &&
           high == app->pulse_stats_last_high_cycles &&
           low == app->pulse_stats_last_low_cycles) {
            return;
        }
        app->pulse_stats_last_high_cycles = high;
        app->pulse_stats_last_low_cycles = low;
        app->pulse_stats_last_valid = true;
    }

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
    if(app->screen == LabMateScreenFrequency ||
       (app->screen == LabMateScreenLogger && app->logger_source != LoggerPulse)) {

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
    if(app->screen == LabMateScreenPulse ||
       (app->screen == LabMateScreenLogger && app->logger_source == LoggerPulse)) {
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
            /* Signal returned later must start a fresh fast median window.
             * Preserve previous MIN/MAX until the user resets them. */
            pulse_stats_window_reset(app);
        }

        app->edges = count;
        app->pulse_high_valid = hi_valid;
        app->pulse_low_valid = lo_valid;
        app->pulse_high_cycles = hi;
        app->pulse_low_cycles = lo;
        pulse_recalculate(app);
        pulse_stats_record(app, now);
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


/* ---------- DATA LOGGER v1.5 ---------- */
/* The capture engine is unchanged; only processed snapshots are persisted.
 * File writes happen in the main thread AFTER releasing the GUI mutex.
 */
static void logger_capture_stop(LabMateApp* app) {
    frequency_hw_stop(app);
    frequency_interrupt_stop(app);
    pulse_interrupt_stop(app);
    gpio_release(app->gpio_index);
}

static void logger_capture_start(LabMateApp* app) {
    app->hold = false;
    app->gpio_index =
        (app->logger_source == LoggerFrequencyHigh) ? 4U : 1U;
    measurement_reset(app);

    if(app->logger_source == LoggerPulse) {
        pulse_stats_reset(app);
        pulse_interrupt_start(app);
    } else {
        frequency_stats_reset(app);
        if(app->logger_source == LoggerFrequencyHigh) {
            frequency_hw_start(app);
        } else {
            frequency_interrupt_start(app);
        }
    }
}

static void logger_capture_change(LabMateApp* app, int8_t direction) {
    if(app->logger_recording) return;
    logger_capture_stop(app);
    if(direction > 0) {
        app->logger_source =
            (app->logger_source + 1U) % LoggerSourceCount;
    } else {
        app->logger_source =
            (app->logger_source + LoggerSourceCount - 1U) % LoggerSourceCount;
    }
    logger_capture_start(app);
}

static void logger_stop(LabMateApp* app) {
    app->logger_recording = false;
    if(app->logger_file) {
        const bool was_open = storage_file_is_open(app->logger_file);
        if(was_open && !storage_file_sync(app->logger_file)) {
            app->logger_error = true;
        }
        /* Storage requires close even if an earlier open failed. A handle
         * that was never opened need not turn an existing error into a
         * second close error. Keep all SD work outside the GUI mutex. */
        if(!storage_file_close(app->logger_file) && was_open) {
            app->logger_error = true;
        }
        storage_file_free(app->logger_file);
        app->logger_file = NULL;
    }
    if(app->logger_storage) {
        furi_record_close(RECORD_STORAGE);
        app->logger_storage = NULL;
    }
}

/* Accept only log_0001.csv through log_9999.csv. */
static bool logger_filename_id(const char* name, uint16_t* result) {
    if(strlen(name) != 12U || strncmp(name, "log_", 4U) != 0 ||
       strcmp(name + 8, ".csv") != 0) return false;
    uint16_t id = 0U;
    for(size_t i = 4U; i < 8U; ++i) {
        if(name[i] < '0' || name[i] > '9') return false;
        id = (uint16_t)(id * 10U + (uint16_t)(name[i] - '0'));
    }
    if(id == 0U) return false;
    *result = id;
    return true;
}

/* Read the highest existing CSV ID once per application session.
 * Keep naming monotonic even if older files were deleted. All filesystem
 * work occurs from the app loop, after releasing the UI mutex. */
static bool logger_init_next_file_index(LabMateApp* app) {
    if(app->logger_next_file_index != 0U) return true;
    File* dir = storage_file_alloc(app->logger_storage);
    if(!dir) return false;

    bool ok = storage_dir_open(dir, LOGGER_DIR);
    uint16_t max_id = 0U;
    if(ok) {
        FileInfo info;
        char name[64];
        while(storage_dir_read(dir, &info, name, sizeof(name))) {
            uint16_t id;
            if(!file_info_is_dir(&info) &&
               logger_filename_id(name, &id) && id > max_id) {
                max_id = id;
            }
        }
        FS_Error error = storage_file_get_error(dir);
        if(error != FSE_NOT_EXIST && error != FSE_OK) ok = false;
    }
    /* Storage API requires close even after a failed open. */
    if(!storage_dir_close(dir)) ok = false;
    storage_file_free(dir);
    if(ok) app->logger_next_file_index = (uint32_t)max_id + 1U;
    return ok;
}

static bool logger_start(LabMateApp* app) {
    if(app->logger_recording) return true;
    app->logger_error = false;
    app->logger_rows = 0U;
    app->logger_path[0] = '\0';

    app->logger_storage = furi_record_open(RECORD_STORAGE);
    if(!app->logger_storage ||
       storage_sd_status(app->logger_storage) != FSE_OK ||
       !storage_simply_mkdir(app->logger_storage, LOGGER_DIR)) {
        app->logger_error = true;
        logger_stop(app);
        return false;
    }

    if(!logger_init_next_file_index(app)) {
        app->logger_error = true;
        logger_stop(app);
        return false;
    }

    app->logger_file = storage_file_alloc(app->logger_storage);
    if(!app->logger_file) {
        app->logger_error = true;
        logger_stop(app);
        return false;
    }

    bool opened = false;
    /* Skip old IDs, including when files have been deleted; if the app is
     * restarted, a one-time scan chooses highest existing ID + 1.
     * This also avoids blocking opens on paths known to exist. */
    uint32_t first_index = app->logger_next_file_index;
    for(uint32_t i = first_index; i <= 9999U; ++i) {
        snprintf(
            app->logger_path, sizeof(app->logger_path),
            LOGGER_DIR "/log_%04lu.csv", (unsigned long)i);
        if(storage_file_exists(app->logger_storage, app->logger_path)) continue;
        /* CREATE_NEW is still essential for no-overwrite safety. */
        if(storage_file_open(
               app->logger_file, app->logger_path, FSAM_WRITE, FSOM_CREATE_NEW)) {
            opened = true;
            app->logger_next_file_index = i + 1U;
            break;
        }
        /* Handle the rare case another app created the file after our
         * existence check; all other errors should stop the search. */
        if(storage_file_get_error(app->logger_file) != FSE_EXIST) break;
    }

    if(!opened) {
        app->logger_error = true;
        logger_stop(app);
        return false;
    }

    const char* header =
        "elapsed_ms,source,pin,valid,frequency_hz,high_us,low_us,period_us,duty_pct\n";
    const size_t header_size = strlen(header);
    if(storage_file_write(app->logger_file, header, header_size) != header_size) {
        app->logger_error = true;
        logger_stop(app);
        return false;
    }

    app->logger_start_tick = furi_get_tick();
    app->logger_last_tick = app->logger_start_tick;
    app->logger_recording = true;
    return true;
}

/* Called with the app mutex held; does not perform storage operations. */
static bool logger_prepare_row(LabMateApp* app, char* row, size_t capacity) {
    if(!app->logger_recording) return false;
    const uint32_t now = furi_get_tick();
    const uint32_t hz = furi_kernel_get_tick_frequency();
    const uint32_t interval =
        (uint32_t)(((uint64_t)hz * LOGGER_INTERVAL_MS + 999ULL) / 1000ULL);
    if((uint32_t)(now - app->logger_last_tick) < (interval ? interval : 1U)) {
        return false;
    }
    app->logger_last_tick = now;
    const uint32_t elapsed_ms =
        hz ? (uint32_t)(((uint64_t)(now - app->logger_start_tick) * 1000ULL) / hz) : 0U;

    int length;
    if(app->logger_source == LoggerPulse) {
        const bool valid = app->pulse_period_valid;
        length = snprintf(
            row, capacity,
            "%lu,PULSE,PC1,%u,,%lu,%lu,%lu,%lu.%01lu\n",
            (unsigned long)elapsed_ms, valid ? 1U : 0U,
            (unsigned long)(valid ? pulse_cycles_to_us(app->pulse_high_cycles) : 0U),
            (unsigned long)(valid ? pulse_cycles_to_us(app->pulse_low_cycles) : 0U),
            (unsigned long)(valid ? pulse_cycles_to_us(app->pulse_period_cycles) : 0U),
            (unsigned long)(valid ? app->pulse_duty_permille / 10U : 0U),
            (unsigned long)(valid ? app->pulse_duty_permille % 10U : 0U));
    } else {
        const bool valid = app->frequency_valid;
        const uint32_t mhz = valid ? app->frequency_millihz : 0U;
        length = snprintf(
            row, capacity,
            "%lu,FREQ,%s,%u,%lu.%03lu,,,,\n",
            (unsigned long)elapsed_ms,
            app->logger_source == LoggerFrequencyHigh ? "PB3" : "PC1",
            valid ? 1U : 0U,
            (unsigned long)(mhz / 1000U),
            (unsigned long)(mhz % 1000U));
    }

    if(length <= 0 || (size_t)length >= capacity) {
        app->logger_error = true;
        app->logger_recording = false;
        app->logger_busy = true;
        app->logger_busy_stopping = true;
        /* The application loop closes the file after releasing the UI mutex. */
        return false;
    }
    return true;
}


/* ---------- READ-ONLY LOG HISTORY v1.5 ---------- */
/* No delete/rename/truncate calls are made from the history browser. */

/* Called without the UI mutex; copies the result under the mutex. */
static void history_scan(LabMateApp* app) {
    uint16_t latest[LOGGER_HISTORY_LIMIT] = {0};
    uint8_t count = 0U;
    uint32_t total = 0U;
    bool ok = false;

    Storage* storage = furi_record_open(RECORD_STORAGE);
    File* dir = NULL;
    if(storage && storage_sd_status(storage) == FSE_OK &&
       storage_dir_exists(storage, LOGGER_DIR)) {
        dir = storage_file_alloc(storage);
        if(dir) {
            if(storage_dir_open(dir, LOGGER_DIR)) {
                ok = true;
                FileInfo info;
                char name[64];
                while(storage_dir_read(dir, &info, name, sizeof(name))) {
                    uint16_t id;
                    if(file_info_is_dir(&info) || !logger_filename_id(name, &id)) continue;
                    ++total;
                    uint8_t insert = 0U;
                    while(insert < count && latest[insert] > id) ++insert;
                    if(insert >= LOGGER_HISTORY_LIMIT) continue;
                    if(count < LOGGER_HISTORY_LIMIT) ++count;
                    for(uint8_t j = count - 1U; j > insert; --j) {
                        latest[j] = latest[j - 1U];
                    }
                    latest[insert] = id;
                }
                if(storage_file_get_error(dir) != FSE_NOT_EXIST &&
                   storage_file_get_error(dir) != FSE_OK) ok = false;
            }
            /* Directory handles must be closed even if open fails. */
            storage_dir_close(dir);
            storage_file_free(dir);
        }
    }
    if(storage) furi_record_close(RECORD_STORAGE);

    furi_mutex_acquire(app->mutex, FuriWaitForever);
    app->history_count = ok ? count : 0U;
    app->history_total = ok ? total : 0U;
    app->history_selected = 0U;
    if(ok) memcpy(app->history_ids, latest, sizeof(latest));
    app->history_error = !ok;
    app->history_busy = false;
    furi_mutex_release(app->mutex);
}

static void history_close(LabMateApp* app) {
    if(app->history_file) {
        if(storage_file_is_open(app->history_file)) {
            storage_file_close(app->history_file);
        }
        storage_file_free(app->history_file);
        app->history_file = NULL;
    }
    if(app->history_storage) {
        furi_record_close(RECORD_STORAGE);
        app->history_storage = NULL;
    }
}

/* Called outside the UI mutex; does not interfere with active log files. */
static void history_open(LabMateApp* app) {
    history_close(app);
    bool ok = false;
    Storage* storage = NULL;
    File* file = NULL;
    if(app->history_selected < app->history_count) {
        char path[96];
        snprintf(
            path, sizeof(path), LOGGER_DIR "/log_%04u.csv",
            (unsigned int)app->history_ids[app->history_selected]);
        storage = furi_record_open(RECORD_STORAGE);
        if(storage && storage_sd_status(storage) == FSE_OK) {
            file = storage_file_alloc(storage);
            if(file && storage_file_open(file, path, FSAM_READ, FSOM_OPEN_EXISTING)) {
                ok = true;
            } else if(file) {
                /* Required even on failed open. */
                storage_file_close(file);
            }
        }
    }
    if(!ok) {
        if(file) storage_file_free(file);
        if(storage) furi_record_close(RECORD_STORAGE);
    }
    furi_mutex_acquire(app->mutex, FuriWaitForever);
    app->history_storage = ok ? storage : NULL;
    app->history_file = ok ? file : NULL;
    app->history_rows = 0U;
    app->history_last_ms = 0U;
    app->history_line_ms = 0U;
    app->history_past_header = false;
    app->history_line_has_comma = false;
    app->history_in_timestamp = true;
    app->history_mode = 0U; /* unknown until first data row */
    app->history_first_row_len = 0U;
    app->history_first_row[0] = '\0';
    app->history_error = !ok;
    app->history_loading = ok;
    app->history_busy = false;
    furi_mutex_release(app->mutex);
}

/* Parse at most one small SD chunk per main-loop iteration. */
static void history_read_step(LabMateApp* app) {
    if(!app->history_file || !app->history_loading) return;
    uint8_t bytes[LOGGER_HISTORY_READ_BYTES];
    size_t size = storage_file_read(app->history_file, bytes, sizeof(bytes));
    bool finished = size == 0U;
    bool ok = true;
    if(finished && !storage_file_eof(app->history_file)) ok = false;

    furi_mutex_acquire(app->mutex, FuriWaitForever);
    for(size_t i = 0; i < size; ++i) {
        const char ch = (char)bytes[i];
        if(ch == '\n') {
            if(app->history_past_header && app->history_line_has_comma) {
                if(app->history_rows == 0U) {
                    app->history_first_row[app->history_first_row_len] = '\0';
                    if(strstr(app->history_first_row, ",PULSE,PC1,")) {
                        app->history_mode = 3U;
                    } else if(strstr(app->history_first_row, ",FREQ,PB3,")) {
                        app->history_mode = 2U;
                    } else if(strstr(app->history_first_row, ",FREQ,PC1,")) {
                        app->history_mode = 1U;
                    }
                }
                ++app->history_rows;
                app->history_last_ms = app->history_line_ms;
            }
            app->history_past_header = true;
            app->history_line_has_comma = false;
            app->history_line_ms = 0U;
            app->history_in_timestamp = true;
            continue;
        }
        if(!app->history_past_header) continue;
        if(app->history_rows == 0U &&
           app->history_first_row_len < sizeof(app->history_first_row) - 1U) {
            app->history_first_row[app->history_first_row_len++] = ch;
        }
        if(ch == ',') {
            app->history_line_has_comma = true;
            app->history_in_timestamp = false;
        } else if(app->history_in_timestamp) {
            if(ch >= '0' && ch <= '9' && app->history_line_ms <= 429496729U) {
                app->history_line_ms =
                    app->history_line_ms * 10U + (uint32_t)(ch - '0');
            } else {
                app->history_in_timestamp = false;
            }
        }
    }
    if(finished) {
        app->history_loading = false;
        if(!ok) app->history_error = true;
    }
    furi_mutex_release(app->mutex);
    if(finished) history_close(app);
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
        labmate_generator_frequencies[
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
            labmate_generator_frequencies[app->generator_freq_index],
            50U);
    }
}

/* ---------- DRAWING (stateful screens) ---------- */

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

    case LabMateScreenLogger:
        draw_logger(canvas, app);
        break;

    case LabMateScreenHistory:
        draw_history(canvas, app);
        break;

    case LabMateScreenHistoryDetail:
        draw_history_detail(canvas, app);
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
        screen == LabMateScreenPulse ||
        screen == LabMateScreenLogger;
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
        /* Defer slow microSD START/STOP work until after UI mutex release. */
        bool logger_start_requested = false;
        bool logger_stop_requested = false;
        bool history_scan_requested = false;
        bool history_open_requested = false;
        bool history_close_requested = false;
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
                        app->screen = LabMateScreenLogger;
                        app->logger_source = LoggerFrequencyLow;
                        app->logger_error = false;
                        app->logger_rows = 0U;
                        app->logger_path[0] = '\0';
                        logger_capture_start(app);
                        break;

                    case 5:
                        app->screen = LabMateScreenHistory;
                        app->history_busy = true;
                        app->history_error = false;
                        history_scan_requested = true;
                        break;

                    case 6:
                        app->screen = LabMateScreenAbout;
                        break;
                    }

                } else if(
                    event.key == InputKeyBack) {
                    app->running = false;
                }

            } else if(app->screen == LabMateScreenHistory) {
                if(event.key == InputKeyUp && app->history_count > 0U) {
                    app->history_selected = (uint8_t)(
                        (app->history_selected + app->history_count - 1U) %
                        app->history_count);
                } else if(event.key == InputKeyDown && app->history_count > 0U) {
                    app->history_selected = (uint8_t)(
                        (app->history_selected + 1U) % app->history_count);
                } else if(event.key == InputKeyOk &&
                          !app->history_busy && app->history_count > 0U) {
                    app->screen = LabMateScreenHistoryDetail;
                    app->history_busy = true;
                    history_open_requested = true;
                } else if(event.key == InputKeyBack) {
                    app->screen = LabMateScreenMenu;
                }
            } else if(app->screen == LabMateScreenHistoryDetail) {
                if(event.key == InputKeyBack) {
                    app->screen = LabMateScreenHistory;
                    app->history_loading = false;
                    history_close_requested = true;
                }
            } else if(app->screen == LabMateScreenLogger) {
                if(event.key == InputKeyLeft) {
                    logger_capture_change(app, -1);
                } else if(event.key == InputKeyRight) {
                    logger_capture_change(app, 1);
                } else if(event.key == InputKeyOk) {
                    logger_stop_requested = app->logger_recording;
                    logger_start_requested = !app->logger_recording;
                    app->logger_busy = true;
                    app->logger_busy_stopping = logger_stop_requested;
                    if(logger_stop_requested) app->logger_recording = false;
                } else if(event.key == InputKeyBack) {
                    if(app->logger_recording || app->logger_file || app->logger_storage) {
                        logger_stop_requested = true;
                        app->logger_recording = false;
                        app->logger_busy = true;
                        app->logger_busy_stopping = true;
                    }
                    logger_capture_stop(app);
                    app->screen = LabMateScreenMenu;
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
                            /* Resume with a fresh IRQ and statistics window.
                             * Keep prior recorded extrema across HOLD/LIVE. */
                            pulse_stats_window_reset(app);
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

        char pending_log_row[160];
        bool pending_log = false;
        if(app->screen == LabMateScreenLogger && app->logger_recording) {
            pending_log = logger_prepare_row(app, pending_log_row, sizeof(pending_log_row));
        }
        if(app->logger_busy && app->logger_error &&
           !logger_start_requested && !logger_stop_requested &&
           (app->logger_file || app->logger_storage)) {
            logger_stop_requested = true;
        }
        furi_mutex_release(
            app->mutex);

        if(logger_start_requested || logger_stop_requested) {
            /* Display OPENING/SAVING without holding the drawing mutex
             * while storage blocks. The main loop may still wait for SD. */
            view_port_update(viewport);
            if(logger_stop_requested) logger_stop(app);
            else logger_start(app);
            furi_mutex_acquire(app->mutex, FuriWaitForever);
            app->logger_busy = false;
            furi_mutex_release(app->mutex);
        }

        /* History directory/file operations never hold the UI mutex. */
        if(history_close_requested) history_close(app);
        if(history_scan_requested) history_scan(app);
        if(history_open_requested) history_open(app);
        if(app->screen == LabMateScreenHistoryDetail && app->history_loading) {
            history_read_step(app);
        }

        /* SD writes stay outside the mutex and never occur in capture IRQs. */
        if(pending_log) {
            size_t bytes = strlen(pending_log_row);
            bool ok = app->logger_file &&
                storage_file_write(app->logger_file, pending_log_row, bytes) == bytes;
            /* Periodic sync happens outside the GUI mutex and outside IRQs.
             * STOP/BACK still syncs and closes the file immediately. */
            if(ok && ((app->logger_rows + 1U) % LOGGER_SYNC_EVERY_ROWS) == 0U) {
                ok = storage_file_sync(app->logger_file);
            }
            furi_mutex_acquire(app->mutex, FuriWaitForever);
            if(ok) {
                app->logger_rows++;
            } else {
                app->logger_error = true;
                app->logger_recording = false;
                app->logger_busy = true;
                app->logger_busy_stopping = true;
            }
            furi_mutex_release(app->mutex);
            if(!ok) {
                logger_stop(app);
                furi_mutex_acquire(app->mutex, FuriWaitForever);
                app->logger_busy = false;
                furi_mutex_release(app->mutex);
            }
        }

        /* Under heavy IRQ load, use a calmer LCD refresh rate while
         * preserving immediate response to keys and all captured edges.
         */
        if(app->screen == LabMateScreenPulse ||
           (app->screen == LabMateScreenLogger && app->logger_source == LoggerPulse)) {
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

    if(app->logger_recording || app->logger_file || app->logger_storage) {
        logger_stop(app);
    }
    history_close(app);

    if(screen_uses_gpio(app->screen)) {
        if(app->screen == LabMateScreenLogger) {
            logger_capture_stop(app);
        } else if(app->screen == LabMateScreenPulse) {
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
























































