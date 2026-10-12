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
    /* A new hardware session restarts TIM2 at zero but keeps the software total. */
    assert(labmate_counter_accumulate(123U, 0U, 27U) == 150U);
    /* RUN=1.5 seconds, STOP indefinitely, RUN=0.75 seconds -> 2.25 seconds. */
    uint64_t active_ticks = labmate_counter_add_ticks(0U, 1500U);
    assert(labmate_counter_elapsed_seconds(active_ticks, 1000U) == 1U);
    active_ticks = labmate_counter_add_ticks(active_ticks, 750U);
    assert(active_ticks == 2250U);
    assert(labmate_counter_elapsed_seconds(active_ticks, 1000U) == 2U);
    assert(labmate_counter_add_ticks(UINT64_MAX - 1U, 3U) == UINT64_MAX);
    assert(labmate_counter_elapsed_seconds(UINT64_MAX, 1U) == UINT32_MAX);
    assert(labmate_counter_elapsed_seconds(9999U, 0U) == 0U);
    char formatted[24];
    char too_small[2];
    assert(labmate_counter_format(0U, formatted, sizeof(formatted)));
    assert(formatted[0] == '0' && formatted[1] == '\0');
    assert(labmate_counter_format(18446744073709551615ULL, formatted, sizeof(formatted)));
    assert(strcmp(formatted, "18446744073709551615") == 0);
    assert(!labmate_counter_format(123U, too_small, sizeof(too_small)));
    assert(too_small[0] == '\0');
    puts("Event Counter TIM2 wrap, pause/resume elapsed math, saturation and decimal formatting PASS");
    return 0;
}
