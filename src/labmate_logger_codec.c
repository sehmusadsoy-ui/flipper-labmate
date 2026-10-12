#include "labmate_logger_codec.h"
#include <stdio.h>
#include <string.h>

bool labmate_logger_filename_id(const char* name, uint16_t* result) {
    if(!name || !result || strlen(name) != 12U ||
       strncmp(name, "log_", 4U) != 0 ||
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

int labmate_logger_format_row(char* row, size_t capacity, const LabMateLogRow* sample) {
    if(!row || !sample || capacity == 0U) return -1;
    if(sample->source == LabMateLogRowPulse) {
        return snprintf(
            row, capacity,
            "%lu,PULSE,PC1,%u,,%lu,%lu,%lu,%lu.%01lu\n",
            (unsigned long)sample->elapsed_ms, sample->valid ? 1U : 0U,
            (unsigned long)(sample->valid ? sample->pulse_high_us : 0U),
            (unsigned long)(sample->valid ? sample->pulse_low_us : 0U),
            (unsigned long)(sample->valid ? sample->pulse_period_us : 0U),
            (unsigned long)(sample->valid ? sample->pulse_duty_permille / 10U : 0U),
            (unsigned long)(sample->valid ? sample->pulse_duty_permille % 10U : 0U));
    }
    if(sample->source == LabMateLogRowFrequencyLow ||
       sample->source == LabMateLogRowFrequencyHigh) {
        const uint32_t mhz = sample->valid ? sample->frequency_millihz : 0U;
        return snprintf(
            row, capacity,
            "%lu,FREQ,%s,%u,%lu.%03lu,,,,\n",
            (unsigned long)sample->elapsed_ms,
            sample->source == LabMateLogRowFrequencyHigh ? "PB3" : "PC1",
            sample->valid ? 1U : 0U,
            (unsigned long)(mhz / 1000U),
            (unsigned long)(mhz % 1000U));
    }
    return -1;
}
