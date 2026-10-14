#pragma once

/* Internal LabMate application state, shared by the app loop and state-aware
 * renderers. NOT an external ABI. v1.6.1 development branch remains separate from Stable.
 * IRQ-owned fields and storage handles retain the v1.5 layout and semantics.
 */
#include <furi.h>
#include <gui/gui.h>
#include <storage/storage.h>
#include "labmate_resource_policy.h"
#include "labmate_navigation.h"
#include "labmate_profile_storage.h"
#include "labmate_pulse_math.h"
#include "labmate_button_logic.h"
#include "labmate_threshold.h"
#include "labmate_uart.h"
#include "labmate_comm_resource.h"
#include "labmate_onewire_hw.h"

#define LABMATE_VERSION_TEXT "v1.8DEV"
/* Shared menu/pin counts: UI and input handling must agree. */
#define MENU_COUNT LabMateToolCount
#define GPIO_COUNT LABMATE_MONITOR_PIN_COUNT
/* Shared immutable GPIO labels, used by both migrated and legacy renderers. */
extern const char* const labmate_gpio_names[GPIO_COUNT];
/* TIM1/PA7 presets live in labmate_generator.c and are shared with UI. */
extern const uint32_t labmate_generator_frequencies[];
/* Keep only the latest 32 log IDs in RAM; read CSV contents incrementally. */
#define LOGGER_HISTORY_LIMIT 32U
/* High-speed pulse extrema use median-of-five sampled readings. */
#define PULSE_STATS_FILTER_SAMPLES LABMATE_PULSE_MEDIAN_SAMPLES

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
    LabMateScreenProfiles,
    LabMateScreenCounter, /* append: preserve existing screen numbers */
    LabMateScreenButton, /* append: preserve original 0..10 */
    LabMateScreenAlerts, /* configuration: no extra GPIO ownership */
    LabMateScreenUart, /* v1.8 UART: append, preserve stable screen IDs */
    LabMateScreenOneWire, /* append only; previous screen IDs preserved */
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
    uint8_t about_page; /* 0 overview, 1 repository, 2..12 tool quick guides */
    uint8_t gpio_index;
    uint8_t preferred_frequency_pin;
    uint8_t preferred_pulse_pin;

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

    /* Event Counter: true PB3/TIM2 rising-edge counts, not rate estimates. */
    bool counter_active;
    uint32_t counter_last_hw;
    uint64_t counter_total;
    uint32_t counter_start_tick; /* tick at beginning of current RUN segment */
    uint64_t counter_elapsed_ticks; /* completed RUN segments; STOP time excluded */
    uint32_t counter_elapsed_seconds;

    /* Button Analyzer: ISR raw edges + app-thread debounced snapshot.
     * PC1 EXTI1 with internal pull-up, LOW = pressed contact.
     */
    bool button_active;
    bool button_session_started; /* STOP preserves results; OK RESUMEs */
    bool button_details_view; /* alternate compact 128x64 metrics page */
    uint8_t button_quiet_index; /* 0..3: 5/10/20/50 ms */
    uint8_t button_quiet_ms;
    volatile LabMateButtonState button_irq;
    LabMateButtonStats button_stats;
    uint32_t button_bounce_us;
    uint32_t button_settle_ms;
    uint32_t button_hold_ms;

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

    /* PWM Studio / TIM1 PA7. Runtime values persist across menu navigation.
     * v1.6 profile records retain preset index only (0..14).
     * Custom editing is STOP-only; no draft reaches TIM1.
     */
    bool generator_running;
    bool generator_state;
    uint8_t generator_freq_index; /* 0..14 presets, 15 = CUSTOM */
    uint8_t generator_duty_percent; /* 5..95; default 50 */
    uint32_t generator_custom_hz; /* committed custom frequency */
    uint32_t generator_custom_draft_hz;
    uint8_t generator_custom_step_index; /* 1/10/100/1000 Hz */
    uint8_t generator_edit_original_index;
    bool generator_editing;
    bool generator_skip_entry_ok; /* ignore menu OK release on first entry */
    uint32_t generator_last_toggle;

    /* Threshold Alerts: one active visual alert, app-thread only. */
    LabMateThreshold threshold;

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

    /* Bounded history browser. CSV reads are streamed; deletion is an
     * explicit second-confirmed, app-thread-only operation on one log ID. */
    uint16_t history_ids[LOGGER_HISTORY_LIMIT];
    uint8_t history_count;
    uint8_t history_selected;
    uint32_t history_total;
    bool history_busy;
    bool history_error;
    bool history_loading;
    bool history_delete_mode; /* LEFT/RIGHT toggles VIEW or DELETE */
    bool history_delete_confirm; /* BACK cancels, OK confirms exact file */
    uint8_t history_delete_notice; /* 0=none, 1=deleted, 2=delete failed */
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

    LabMateUart uart; /* USART external GPIO 13/14, no TIM1/TIM2 ownership */

    LabMateProfileStore profiles;
    uint8_t profile_active_copy; /* 0=a, 1=b, 255=none */
    uint8_t profile_selected;
    uint8_t profile_action; /* 0=LOAD 1=SAVE 2=DELETE */
    bool profile_confirm;
    bool profile_busy;
    LabMateProfileIoResult profile_io;
    uint8_t profile_notice; /* 0=ready 1=saved 2=loaded 3=empty 4=stop PWM 5=error 6=deleted */

    FuriMutex* mutex;
} LabMateApp;

/* Shared original DWT cycle->us conversion (measurement and passive UI). */
uint64_t pulse_cycles_to_us(uint32_t cycles);
