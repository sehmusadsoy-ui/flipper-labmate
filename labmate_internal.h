#pragma once

/* Internal LabMate application state, shared by the app loop and state-aware
 * renderers. NOT an external ABI. Changes must stay on v1.6-dev until tested.
 * IRQ-owned fields and storage handles retain the v1.5 layout and semantics.
 */
#include <furi.h>
#include <gui/gui.h>
#include <storage/storage.h>
#include "labmate_resource_policy.h"
#include "labmate_navigation.h"

#define LABMATE_VERSION_TEXT "v1.6d"
/* Shared menu/pin counts: UI and input handling must agree. */
#define MENU_COUNT LabMateToolCount
#define GPIO_COUNT LABMATE_MONITOR_PIN_COUNT
/* Shared immutable GPIO labels, used by both migrated and legacy renderers. */
extern const char* const labmate_gpio_names[GPIO_COUNT];
/* One source of truth for TIM1/PA7 preset frequencies, also displayed in UI. */
extern const uint32_t labmate_generator_frequencies[];
/* Keep only the latest 32 log IDs in RAM; read CSV contents incrementally. */
#define LOGGER_HISTORY_LIMIT 32U
/* High-speed pulse extrema use median-of-five sampled readings. */
#define PULSE_STATS_FILTER_SAMPLES 5U

typedef enum {
    LabMateScreenMenu,
    LabMateScreenGpio,
    LabMateScreenFrequency,
    LabMateScreenPulse,
    LabMateScreenGenerator,
    LabMateScreenLogger,
    LabMateScreenHistory,
    LabMateScreenHistoryDetail,
    LabMateScreenAbout,
} LabMateScreen;

typedef enum {
    LoggerFrequencyLow,
    LoggerFrequencyHigh,
    LoggerPulse,
    LoggerSourceCount,
} LabMateLoggerSource;

typedef struct {
    uint32_t high_cycles;
    uint32_t low_cycles;
    uint32_t period_cycles;
    uint32_t duty_permille;
} PulseStatsSample;

typedef struct {
    bool running;
    bool hold;

    uint8_t selected; /* active row within root or current tool group */
    bool menu_in_group;
    uint8_t menu_group; /* LabMateMenuGroup, valid when menu_in_group */
    uint8_t gpio_index;

    LabMateScreen screen;
    /* One active measurement capture at a time; TIM1 PWM is independent. */
    LabMateCaptureOwner capture_owner;
    /* Physical pin armed by capture; independent of the selected UI pin. */
    uint8_t capture_pin_index;
    /* Software-policy denial only; not low-level hardware fault detection. */
    bool capture_blocked;

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
    /* True only after an input edge has been observed in this gate. */
    bool frequency_hw_gate_started;
    /* First sample of the adaptive frequency-estimation gate. */
    uint32_t frequency_hw_last_count;
    uint32_t frequency_hw_last_cycle;
    /* Last 100 ms counter poll: independent of gate origin and HOLD. */
    uint32_t frequency_hw_last_poll_count;
    uint32_t frequency_hw_last_poll_cycle;

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
    PulseStatsSample pulse_stats_recent[PULSE_STATS_FILTER_SAMPLES];
    uint8_t pulse_stats_recent_count;
    uint8_t pulse_stats_recent_next;
    uint32_t pulse_stats_recent_tick;
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

    /* v1.5: SD logging uses app-thread snapshots, never GPIO IRQ writes. */
    LabMateLoggerSource logger_source;
    bool logger_recording;
    bool logger_error;
    bool logger_busy;
    bool logger_busy_stopping;
    uint32_t logger_next_file_index;
    uint32_t logger_start_tick;
    uint32_t logger_last_tick;
    uint32_t logger_rows;
    char logger_path[96];
    Storage* logger_storage;
    File* logger_file;

    /* Read-only history browser. The list is bounded; CSV parsing is streamed. */
    uint16_t history_ids[LOGGER_HISTORY_LIMIT];
    uint8_t history_count;
    uint8_t history_selected;
    uint32_t history_total;
    bool history_busy;
    bool history_error;
    bool history_loading;
    Storage* history_storage;
    File* history_file;
    uint32_t history_rows;
    uint32_t history_last_ms;
    uint32_t history_line_ms;
    bool history_past_header;
    bool history_line_has_comma;
    bool history_in_timestamp;
    uint8_t history_mode;
    char history_first_row[80];
    uint8_t history_first_row_len;

    FuriMutex* mutex;
} LabMateApp;

/* Shared original DWT cycle->us conversion (measurement and passive UI). */
uint64_t pulse_cycles_to_us(uint32_t cycles);
