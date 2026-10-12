#pragma once

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* Unsigned TIM2 snapshots are edge counts, not estimated frequency.
 * One 32-bit wrap is handled between consecutive polls; caller guarantees
 * fewer than 2^32 incoming edges per poll interval.
 */
uint64_t labmate_counter_accumulate(uint64_t total, uint32_t previous, uint32_t current);
/* Decimal rendering without depending on embedded libc support for %llu. */
bool labmate_counter_format(uint64_t count, char* output, size_t capacity);
