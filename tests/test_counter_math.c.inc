/* Host-only tests. These bytes are not linked into the FAP. */
#include "labmate_counter_math.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    assert(labmate_counter_accumulate(0U, 0U, 0U) == 0U);
    assert(labmate_counter_accumulate(0U, 0U, 3U) == 3U);
    assert(labmate_counter_accumulate(3U, 3U, 9U) == 9U);
    assert(labmate_counter_accumulate(100U, UINT32_MAX - 1U, 2U) == 104U);
    assert(labmate_counter_accumulate(0U, UINT32_MAX, 0U) == 1U);
    assert(labmate_counter_accumulate(UINT64_MAX - 2U, 0U, 10U) == UINT64_MAX);
    assert(labmate_counter_accumulate(UINT64_MAX, 11U, 12U) == UINT64_MAX);
    assert(labmate_counter_accumulate(45U, 777U, 777U) == 45U);
    char formatted[24];
    char too_small[2];
    assert(labmate_counter_format(0U, formatted, sizeof(formatted)));
    assert(formatted[0] == '0' && formatted[1] == '\0');
    assert(labmate_counter_format(18446744073709551615ULL, formatted, sizeof(formatted)));
    assert(strcmp(formatted, "18446744073709551615") == 0);
    assert(!labmate_counter_format(123U, too_small, sizeof(too_small)));
    assert(too_small[0] == '\0');
    puts("Event Counter TIM2 wrap/saturation and decimal formatting tests PASS");
    return 0;
}
