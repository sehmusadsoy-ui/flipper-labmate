#include "labmate_counter_math.h"

#include <stdint.h>

uint64_t labmate_counter_accumulate(uint64_t total, uint32_t previous, uint32_t current) {
    const uint32_t delta = (uint32_t)(current - previous);
    if(UINT64_MAX - total < (uint64_t)delta) return UINT64_MAX;
    return total + (uint64_t)delta;
}

bool labmate_counter_format(uint64_t count, char* output, size_t capacity) {
    if(!output || capacity == 0U) return false;
    char reversed[20];
    size_t digits = 0U;
    do {
        reversed[digits++] = (char)('0' + (count % 10U));
        count /= 10U;
    } while(count != 0U);
    if(capacity <= digits) {
        output[0] = '\0';
        return false;
    }
    for(size_t i = 0U; i < digits; ++i) {
        output[i] = reversed[digits - i - 1U];
    }
    output[digits] = '\0';
    return true;
}
