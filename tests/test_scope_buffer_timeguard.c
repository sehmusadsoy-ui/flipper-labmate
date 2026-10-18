/* Host-only regression of LabMate's bounded digital edge buffer and timeguard.
 * No firmware, Flipper, GPIO or MCU header dependency.
 * Build from repository root:
 * cc -std=c11 -Wall -Wextra -Werror -pedantic -Isrc \
 *   tests/test_scope_buffer_timeguard.c src/labmate_scope_buffer.c \
 *   src/labmate_scope_timeguard.c -o /tmp/labmate-scope-host
 * /tmp/labmate-scope-host
 */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "labmate_scope_buffer.h"
#include "labmate_scope_timeguard.h"

static void test_reject_invalid_and_trigger_filter(void) {
    LabMateScopeBuffer b = {0};
    LabMateScopeEdge store[3] = {0};
    assert(!labmate_scope_buffer_init(NULL, store, 3));
    assert(!labmate_scope_buffer_init(&b, NULL, 3));
    assert(!labmate_scope_buffer_init(&b, store, 0));
    assert(!labmate_scope_buffer_init(&b, store, LABMATE_SCOPE_MAX_EDGES + 1U));
    assert(labmate_scope_buffer_init(&b, store, 3));
    assert(!labmate_scope_buffer_arm(&b, (LabMateScopeTrigger)99, false));
    assert(b.state == LabMateScopeIdle);
    assert(labmate_scope_buffer_arm(&b, LabMateScopeTriggerRising, true));
    assert(!labmate_scope_buffer_push_edge(&b, 10, true));  /* duplicate */
    assert(!labmate_scope_buffer_push_edge(&b, 11, false)); /* unmatched FALL */
    assert(b.count == 0 && b.state == LabMateScopeArmed);
    assert(labmate_scope_buffer_push_edge(&b, 12, true));
    assert(b.count == 1 && b.edges[0].tick == 12 && b.edges[0].delta_ticks == 0);
    assert(!labmate_scope_buffer_arm(&b, LabMateScopeTriggerEither, false));
    labmate_scope_buffer_stop(&b);
    assert(b.state == LabMateScopeStopped && b.count == 1);
    assert(labmate_scope_buffer_arm(&b, LabMateScopeTriggerEither, false));
    assert(b.count == 0 && b.dropped_edges == 0 && !b.overflowed);
}

static void test_short_wrap_and_clock_failure(void) {
    LabMateScopeBuffer b = {0};
    LabMateScopeEdge store[3] = {0};
    assert(labmate_scope_buffer_init(&b, store, 3));
    assert(labmate_scope_buffer_arm(&b, LabMateScopeTriggerEither, false));
    assert(labmate_scope_buffer_push_edge(&b, UINT32_MAX - 9U, true));
    assert(labmate_scope_buffer_push_edge(&b, 5U, false));
    assert(b.count == 2 && b.edges[1].delta_ticks == 15U);
    assert(!labmate_scope_buffer_push_edge(&b, 5U, true)); /* 0 delta ambiguous */
    assert(b.state == LabMateScopeError && b.timebase_error);
    labmate_scope_buffer_stop(&b);
    assert(labmate_scope_buffer_arm(&b, LabMateScopeTriggerEither, false));
    assert(labmate_scope_buffer_push_edge(&b, 10, true));
    assert(!labmate_scope_buffer_push_edge(
        &b, (uint32_t)(10U + LABMATE_SCOPE_MAX_SAFE_DELTA + 1U), false));
    assert(b.timebase_error && b.state == LabMateScopeError);
}

static void test_bounded_full_and_drop(void) {
    LabMateScopeBuffer b = {0};
    LabMateScopeEdge store[LABMATE_SCOPE_MAX_EDGES] = {0};
    assert(labmate_scope_buffer_init(&b, store, LABMATE_SCOPE_MAX_EDGES));
    assert(labmate_scope_buffer_arm(&b, LabMateScopeTriggerEither, false));
    for(uint32_t i = 0; i < LABMATE_SCOPE_MAX_EDGES; ++i) {
        assert(labmate_scope_buffer_push_edge(&b, i + 1U, (i % 2U) == 0U));
    }
    assert(b.count == LABMATE_SCOPE_MAX_EDGES && !b.overflowed);
    assert(!labmate_scope_buffer_push_edge(
        &b, LABMATE_SCOPE_MAX_EDGES + 1U, true));
    LabMateScopeSnapshot s = labmate_scope_buffer_snapshot(&b);
    assert(s.count == LABMATE_SCOPE_MAX_EDGES);
    assert(s.overflowed && s.dropped_edges == 1U && s.state == LabMateScopeFull);
    assert(!labmate_scope_buffer_push_edge(
        &b, LABMATE_SCOPE_MAX_EDGES + 2U, false));
    assert(b.dropped_edges == 2U);
    labmate_scope_buffer_stop(&b);
    assert(b.count == LABMATE_SCOPE_MAX_EDGES && b.overflowed);
}

static LabMateScopeSnapshot snap(LabMateScopeState state, uint16_t count) {
    LabMateScopeSnapshot s = {0};
    s.state = state;
    s.count = count;
    s.capacity = LABMATE_SCOPE_MAX_EDGES;
    return s;
}

static void test_timeguard_trigger_quiet_and_wrap(void) {
    LabMateScopeTimeguard g = {0};
    assert(!labmate_scope_timeguard_init(&g, 0, 200, 150, 1000, 101));
    assert(labmate_scope_timeguard_init(&g, 0, 200, 150, 1000, 50));
    for(uint32_t t = 50; t < 200; t += 50) {
        assert(labmate_scope_timeguard_poll(&g, t, snap(LabMateScopeArmed, 0))
            == LabMateScopeGuardRunning);
    }
    assert(labmate_scope_timeguard_poll(&g, 200, snap(LabMateScopeArmed, 0))
        == LabMateScopeGuardNoTrigger);
    assert(labmate_scope_timeguard_poll(&g, 250, snap(LabMateScopeArmed, 0))
        == LabMateScopeGuardNoTrigger); /* terminal sticky */

    assert(labmate_scope_timeguard_init(&g, 0, 200, 150, 1000, 50));
    assert(labmate_scope_timeguard_poll(&g, 50, snap(LabMateScopeRecording, 1))
        == LabMateScopeGuardRunning);
    assert(labmate_scope_timeguard_poll(&g, 100, snap(LabMateScopeRecording, 1))
        == LabMateScopeGuardRunning);
    assert(labmate_scope_timeguard_poll(&g, 150, snap(LabMateScopeRecording, 1))
        == LabMateScopeGuardRunning);
    assert(labmate_scope_timeguard_poll(&g, 200, snap(LabMateScopeRecording, 1))
        == LabMateScopeGuardQuiet);

    assert(labmate_scope_timeguard_init(&g, UINT32_MAX - 20U, 200, 150, 1000, 50));
    assert(labmate_scope_timeguard_poll(&g, 10U, snap(LabMateScopeArmed, 0))
        == LabMateScopeGuardRunning); /* modulo millisecond wrap */

    assert(labmate_scope_timeguard_init(&g, 0, 200, 150, 1000, 50));
    assert(labmate_scope_timeguard_poll(&g, 51, snap(LabMateScopeArmed, 0))
        == LabMateScopeGuardClockUnsafe);

    assert(labmate_scope_timeguard_init(&g, 0, 200, 150, 1000, 50));
    assert(labmate_scope_timeguard_poll(&g, 50, snap(LabMateScopeRecording, 0))
        == LabMateScopeGuardInvalid);
}

/* Limits, terminal priority and snapshot faults not covered by ordinary
 * 100Hz/1kHz flows. Keep these pure and deterministic on any host. */
static void test_duration_and_terminal_status(void) {
    LabMateScopeTimeguard g = {0};
    assert(!labmate_scope_timeguard_init(&g, 0U, 200U, 150U, 1001U, 0U));
    assert(!labmate_scope_timeguard_init(
        &g, 0U, 200U, 150U, LABMATE_SCOPE_GUARD_MAX_SESSION_MS + 1U, 50U));
    assert(!labmate_scope_timeguard_init(&g, 0U, 300U, 150U, 250U, 50U));
    assert(labmate_scope_timeguard_init(&g, 0U, 200U, 150U, 300U, 50U));
    for(uint32_t t = 50U; t <= 300U; t += 50U) {
        const LabMateScopeGuardResult status = labmate_scope_timeguard_poll(
            &g, t, snap(LabMateScopeRecording, 1U));
        assert(status == (t == 300U ?
            LabMateScopeGuardDurationLimit :
            (t < 200U ? LabMateScopeGuardRunning : LabMateScopeGuardQuiet)));
        if(t == 200U) break; /* quiet is terminal for this session */
    }
    /* A separate capture with fresh edges at each poll reaches session cap. */
    assert(labmate_scope_timeguard_init(&g, 0U, 200U, 150U, 300U, 50U));
    for(uint32_t t = 50U; t <= 300U; t += 50U) {
        const LabMateScopeGuardResult status = labmate_scope_timeguard_poll(
            &g, t, snap(LabMateScopeRecording, (uint16_t)(t / 50U)));
        assert(status == (t == 300U ?
            LabMateScopeGuardDurationLimit : LabMateScopeGuardRunning));
    }
    assert(labmate_scope_timeguard_poll(
        &g, 350U, snap(LabMateScopeRecording, 8U)) ==
        LabMateScopeGuardDurationLimit);
}

static void test_fail_closed_snapshot_and_full(void) {
    LabMateScopeTimeguard g = {0};
    LabMateScopeSnapshot invalid = snap(LabMateScopeArmed, 1U);
    assert(labmate_scope_timeguard_init(&g, 0U, 200U, 150U, 1000U, 50U));
    assert(labmate_scope_timeguard_poll(&g, 50U, invalid) ==
           LabMateScopeGuardInvalid);
    assert(labmate_scope_timeguard_poll(
        &g, 100U, snap(LabMateScopeArmed, 0U)) ==
        LabMateScopeGuardInvalid); /* terminal stays invalid */

    assert(labmate_scope_timeguard_init(&g, 0U, 200U, 150U, 1000U, 50U));
    invalid = snap(LabMateScopeRecording, 2U);
    invalid.overflowed = true;
    invalid.state = LabMateScopeFull;
    assert(labmate_scope_timeguard_poll(&g, 50U, invalid) ==
           LabMateScopeGuardFull);

    assert(labmate_scope_timeguard_init(&g, 0U, 200U, 150U, 1000U, 50U));
    invalid = snap(LabMateScopeError, 1U);
    invalid.timebase_error = true;
    assert(labmate_scope_timeguard_poll(&g, 50U, invalid) ==
           LabMateScopeGuardCaptureError);

    assert(labmate_scope_timeguard_init(&g, 0U, 200U, 150U, 1000U, 50U));
    invalid = snap(LabMateScopeRecording, 2U);
    invalid.capacity = 1U;
    assert(labmate_scope_timeguard_poll(&g, 50U, invalid) ==
           LabMateScopeGuardInvalid);

    assert(labmate_scope_timeguard_init(&g, 0U, 200U, 150U, 1000U, 50U));
    assert(labmate_scope_timeguard_poll(
        &g, 50U, snap(LabMateScopeRecording, 2U)) ==
        LabMateScopeGuardRunning);
    assert(labmate_scope_timeguard_poll(
        &g, 100U, snap(LabMateScopeRecording, 1U)) ==
        LabMateScopeGuardInvalid); /* lost edges are not a valid history */
}

static void test_dropped_counter_saturates(void) {
    LabMateScopeBuffer b = {0};
    LabMateScopeEdge storage[1] = {0};
    assert(labmate_scope_buffer_init(&b, storage, 1U));
    assert(labmate_scope_buffer_arm(&b, LabMateScopeTriggerEither, false));
    assert(labmate_scope_buffer_push_edge(&b, 1U, true));
    assert(!labmate_scope_buffer_push_edge(&b, 2U, false));
    assert(b.state == LabMateScopeFull && b.dropped_edges == 1U);
    b.dropped_edges = UINT32_MAX;
    assert(!labmate_scope_buffer_push_edge(&b, 3U, true));
    assert(b.dropped_edges == UINT32_MAX);
    assert(!labmate_scope_buffer_push_edge(&b, 4U, true));
    assert(b.dropped_edges == UINT32_MAX); /* duplicate not an edge */
    const LabMateScopeSnapshot s = labmate_scope_buffer_snapshot(&b);
    assert(s.overflowed && s.count == 1U && s.dropped_edges == UINT32_MAX);
}

int main(void) {
    test_reject_invalid_and_trigger_filter();
    test_short_wrap_and_clock_failure();
    test_bounded_full_and_drop();
    test_timeguard_trigger_quiet_and_wrap();
    test_duration_and_terminal_status();
    test_fail_closed_snapshot_and_full();
    test_dropped_counter_saturates();
    puts("scope buffer + timeguard host regressions: PASS");
    return 0;
}
