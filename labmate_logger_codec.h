#pragma once
/* Portable v1.6.1 logger CSV and file-ID codec. No Flipper/SD I/O. */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
typedef enum {
    LabMateLogRowFrequencyLow = 0,
    LabMateLogRowFrequencyHigh = 1,
    LabMateLogRowPulse = 2,
} LabMateLogRowSource;
typedef struct {
    LabMateLogRowSource source;
    uint32_t elapsed_ms;
    bool valid;
    uint32_t frequency_millihz;
    uint32_t pulse_high_us;
    uint32_t pulse_low_us;
    uint32_t pulse_period_us;
    uint32_t pulse_duty_permille;
} LabMateLogRow;
/* Only log_0001.csv through log_9999.csv; no filesystem operations. */
bool labmate_logger_filename_id(const char* name, uint16_t* result);
/* Return snprintf length or -1 on invalid inputs. Caller checks capacity. */
int labmate_logger_format_row(char* row, size_t capacity, const LabMateLogRow* sample);
