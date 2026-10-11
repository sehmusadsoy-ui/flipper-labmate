#include "labmate_counter_math.h"

#include <stdint.h>

uint64_t labmate_counter_accumulate(uint64_t total, uint32_t previous, uint32_t current) {
    const uint32_t delta = (uint32_t)(current - previous);
    if(UINT64_MAX - total < (uint64_t)delta) return UINT64_MAX;
    return total + (uint64_t)delta;
}
