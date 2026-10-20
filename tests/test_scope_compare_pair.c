/* Pure C v1.9 Signal Compare regressions. No firmware or Flipper access.
 * cc -std=c11 -Wall -Wextra -Werror -pedantic -Isrc \
 *   tests/test_scope_compare_pair.c src/labmate_scope_compare.c \
 *   src/labmate_scope_pair.c -o /tmp/test_scope_compare_pair
 * /tmp/test_scope_compare_pair
 */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "labmate_scope_pair.h"

static LabMateScopeMetrics good_a(void) {
    /* Two fully observed 1 kHz 50% cycles at 1 MHz timebase. */
    const LabMateScopeEdge edges[] = {
        {.tick = 100U, .delta_ticks = 0U, .high = true},
        {.tick = 600U, .delta_ticks = 500U, .high = false},
        {.tick = 1100U, .delta_ticks = 500U, .high = true},
        {.tick = 1600U, .delta_ticks = 500U, .high = false},
        {.tick = 2100U, .delta_ticks = 500U, .high = true},
    };
    LabMateScopeMetrics m = labmate_scope_metrics_from_edges(edges, 5U, 1000000U);
    assert(m.status == LabMateScopeMetricsReady);
    assert(m.edge_count == 5U && m.completed_cycles == 2U);
    assert(m.frequency_millihz == 1000000U && m.duty_permille == 500U);
    assert(m.min_period_ticks == 1000U && m.max_period_ticks == 1000U);
    return m;
}

static LabMateScopeMetrics good_b(void) {
    /* One observed 1 kHz cycle, HIGH=450us, LOW=550us. */
    const LabMateScopeEdge edges[] = {
        {.tick = 200U, .delta_ticks = 0U, .high = true},
        {.tick = 650U, .delta_ticks = 450U, .high = false},
        {.tick = 1200U, .delta_ticks = 550U, .high = true},
    };
    LabMateScopeMetrics m = labmate_scope_metrics_from_edges(edges, 3U, 1000000U);
    assert(m.status == LabMateScopeMetricsReady);
    assert(m.completed_cycles == 1U);
    assert(m.frequency_millihz == 1000000U && m.duty_permille == 450U);
    return m;
}

static void test_invalid_and_insufficient(void) {
    const LabMateScopeEdge invalid[] = {
        {.tick = 1U, .delta_ticks = 0U, .high = true},
        {.tick = 501U, .delta_ticks = 499U, .high = false}, /* 500 actual */
        {.tick = 1001U, .delta_ticks = 500U, .high = true},
    };
    LabMateScopeMetrics m = labmate_scope_metrics_from_edges(NULL, 0U, 1000000U);
    assert(m.status == LabMateScopeMetricsInsufficient);
    m = labmate_scope_metrics_from_edges(invalid, 2U, 1000000U);
    assert(m.status == LabMateScopeMetricsInsufficient);
    m = labmate_scope_metrics_from_edges(invalid, 3U, 0U);
    assert(m.status == LabMateScopeMetricsClockInvalid);
    m = labmate_scope_metrics_from_edges(invalid, 3U, 1000000U);
    assert(m.status == LabMateScopeMetricsInvalid);
}

static void test_pair_generation_and_truncation(void) {
    const LabMateScopeMetrics a = good_a(), b = good_b();
    LabMateScopePair pair = {0};
    labmate_scope_pair_reset(&pair);
    assert(!labmate_scope_pair_save_b(&pair, &b, 1U));
    assert(pair.notice == LabMateScopePairNeedA);
    assert(!labmate_scope_pair_save_a(&pair, &a, 0U));
    assert(pair.notice == LabMateScopePairInvalidSample);

    LabMateScopeMetrics incomplete = a;
    incomplete.truncated = true; /* FULL / dropped-edge capture */
    assert(!labmate_scope_pair_save_a(&pair, &incomplete, 1U));
    assert(pair.notice == LabMateScopePairInvalidSample);
    assert(!labmate_scope_compare_metrics(&incomplete, &b).comparable);
    assert(!labmate_scope_compare_metrics(&a, &incomplete).comparable);

    assert(labmate_scope_pair_save_a(&pair, &a, 1U));
    assert(pair.has_a && !pair.has_b);
    assert(!labmate_scope_pair_save_b(&pair, &b, 1U));
    assert(pair.notice == LabMateScopePairNeedFreshB);
    incomplete = b;
    incomplete.truncated = true;
    assert(!labmate_scope_pair_save_b(&pair, &incomplete, 2U));
    assert(pair.notice == LabMateScopePairInvalidSample);
    assert(!pair.has_b); /* Invalid capture cannot become a comparison. */

    assert(labmate_scope_pair_save_b(&pair, &b, 2U));
    assert(pair.has_b && pair.delta.comparable);
    assert(pair.delta.frequency_delta_millihz == 0);
    assert(pair.delta.duty_delta_permille == -50);
    assert(!labmate_scope_pair_save_b(&pair, &b, 2U));
    assert(pair.notice == LabMateScopePairNeedFreshB);
    assert(labmate_scope_pair_save_a(&pair, &a, 3U));
    assert(pair.has_a && !pair.has_b && !pair.delta.comparable);
    assert(!labmate_scope_pair_save_b(&pair, &b, 2U));
    assert(pair.notice == LabMateScopePairNeedFreshB);
}

int main(void) {
    test_invalid_and_insufficient();
    test_pair_generation_and_truncation();
    puts("scope Signal Compare and A/B truncated-capture regressions: PASS");
    return 0;
}
