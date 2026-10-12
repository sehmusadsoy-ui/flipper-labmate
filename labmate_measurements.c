#include "labmate_measurements.h"
#include "labmate_frequency_tim2.h"
#include "labmate_frequency_gate.h"
#include "labmate_monitor_gpio.h"
#include "labmate_pulse_math.h"
#include <furi_hal.h>
#include <string.h>

/* App-thread measurement aggregation only. ISR/HAL pin ownership remains
 * with existing capture modules and must never be changed from this file.
 * Identical logic was extracted from the device-tested v1.7 RC1 core. */

void measurement_reset(LabMateApp* app) {
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
void frequency_stats_reset(LabMateApp* app) {
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

/* Convert captured CPU cycles with 64-bit intermediates. */
uint64_t pulse_cycles_to_us(uint32_t cycles) {
    if(SystemCoreClock == 0U) return 0;
    return (((uint64_t)cycles * 1000000ULL) +
            (SystemCoreClock / 2U)) / SystemCoreClock;
}

static void pulse_recalculate(LabMateApp* app) {
    app->pulse_period_valid = false;
    if(!app->pulse_high_valid || !app->pulse_low_valid) return;

    uint32_t period = 0U;
    uint32_t duty = 0U;
    if(!labmate_pulse_period_and_duty(
           app->pulse_high_cycles, app->pulse_low_cycles,
           &period, &duty)) return;
    app->pulse_period_cycles = period;
    app->pulse_duty_permille = duty;
    app->pulse_period_valid = true;
}

/* Keep running extrema across HOLD and signal loss, but discard an
 * incomplete smoothing window whenever the capture source restarts. */
static void pulse_stats_window_reset(LabMateApp* app) {
    app->pulse_stats_recent_count = 0U;
    app->pulse_stats_recent_next = 0U;
    app->pulse_stats_recent_tick = 0U;
}

/* Pure median-of-five extraction is tested in labmate_pulse_math.c.
 * This app-thread statistics window still owns its capture timestamps.
 */
/* The extrema summarize published/averaged HIGH+LOW readings, not
 * individual high-speed edges. Keeping this outside the IRQ preserves
 * the v1.3 capture timing and 50 kHz live duty filtering behavior. */
void pulse_stats_reset(LabMateApp* app) {
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
        high = labmate_pulse_median5(highs);
        low = labmate_pulse_median5(lows);
        period = labmate_pulse_median5(periods);
        duty = labmate_pulse_median5(duties);
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
void measurement_update(LabMateApp* app) {
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
            const uint32_t current_cycle = DWT->CYCCNT;

            /* Poll hardware at ~100 ms to keep high-rate responsiveness.
             * Low-count readings accumulate across multiple polls instead
             * of mistaking one 1 Hz pulse for 10 Hz in a 100 ms gate.
             */
            if(SystemCoreClock > 0U &&
               (uint32_t)(current_cycle - app->frequency_hw_last_poll_cycle) >=
                   (SystemCoreClock / 10U)) {

                const uint32_t current_count = labmate_frequency_tim2_read();
                app->frequency_hw_last_poll_cycle = current_cycle;
                app->edges = current_count;

                /* Invalidate both display and gate after a quiet input.
                 * Check BEFORE updating last-edge time so that an edge
                 * arriving after a long gap cannot publish a stale rate.
                 */
                if(tick_frequency > 0U &&
                   (uint32_t)(now - app->frequency_last_edge) >
                       (tick_frequency * 3U)) {
                    app->frequency_millihz = 0U;
                    app->frequency_valid = false;
                    app->frequency_hw_gate_started = false;
                }

                /* The 100 ms TIM2 poll is not the frequency estimation
                 * window. Anchor the window at an OBSERVED counter change
                 * and only close it at another observed counter change.
                 * This avoids the large +/-one pulse phase error at 1 Hz.
                 */
                if(current_count != app->frequency_hw_last_poll_count) {
                    app->frequency_hw_last_poll_count = current_count;
                    app->frequency_last_edge = now;

                    if(!app->frequency_hw_gate_started) {
                        app->frequency_hw_gate_started = true;
                        app->frequency_hw_last_count = current_count;
                        app->frequency_hw_last_cycle = current_cycle;
                    } else {
                        uint32_t sample_millihz = 0U;
                        const LabMateHighGateResult gate =
                            labmate_high_gate_evaluate(
                                current_count - app->frequency_hw_last_count,
                                (uint32_t)(current_cycle -
                                           app->frequency_hw_last_cycle),
                                SystemCoreClock, &sample_millihz);
                        if(gate != LabMateHighGateWait) {
                            /* This is a counted rising-edge boundary.
                             * Re-arm immediately; high input rates still
                             * publish as often as the ~100 ms poll allows.
                             */
                            app->frequency_hw_last_count = current_count;
                            app->frequency_hw_last_cycle = current_cycle;
                            if(gate == LabMateHighGatePublish) {
                                app->frequency_millihz = sample_millihz;
                                app->frequency_valid = true;
                                frequency_stats_record(app);
                            }
                        }
                    }
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

                    uint32_t sample_millihz = 0U;
                    if(labmate_low_period_to_millihz(
                           average_period, SystemCoreClock, &sample_millihz)) {
                        app->frequency_millihz = sample_millihz;
                        app->frequency_valid = true;
                        frequency_stats_record(app);
                    }
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
    bool current = labmate_monitor_gpio_read(app->gpio_index);
    if(current != app->gpio_previous_state) {
        app->edges++;
        app->gpio_previous_state = current;
    }
    app->gpio_state = current;
}


