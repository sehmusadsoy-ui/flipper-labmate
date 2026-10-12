#include "labmate_logger_snapshot.h"
#include "labmate_logger_codec.h"
#include <furi.h>

#define LOGGER_INTERVAL_MS 1000U

/* App-thread CSV snapshot/formatting; no SD writes or IRQ ownership. */
/* Called with the app mutex held; does not perform storage operations. */
bool logger_prepare_row(LabMateApp* app, char* row, size_t capacity) {
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

    LabMateLogRow sample = {
        .source = (LabMateLogRowSource)app->logger_source,
        .elapsed_ms = elapsed_ms,
        .valid = app->logger_source == LoggerPulse ?
            app->pulse_period_valid : app->frequency_valid,
        .frequency_millihz = app->frequency_millihz,
    };
    if(app->logger_source == LoggerPulse && sample.valid) {
        /* Preserve existing 32-bit ARM snprintf argument semantics. */
        sample.pulse_high_us = (uint32_t)pulse_cycles_to_us(app->pulse_high_cycles);
        sample.pulse_low_us = (uint32_t)pulse_cycles_to_us(app->pulse_low_cycles);
        sample.pulse_period_us = (uint32_t)pulse_cycles_to_us(app->pulse_period_cycles);
        sample.pulse_duty_permille = app->pulse_duty_permille;
    }
    const int length = labmate_logger_format_row(row, capacity, &sample);

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


