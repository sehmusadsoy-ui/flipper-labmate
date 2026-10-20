#include "labmate_scope_buffer.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

static LabMateScopeBuffer fresh(LabMateScopeEdge* buffer, size_t n) {
    LabMateScopeBuffer s;
    assert(labmate_scope_buffer_init(&s, buffer, n));
    return s;
}

static void test_validation(void) {
    LabMateScopeEdge buf[2];
    LabMateScopeBuffer s;
    assert(!labmate_scope_buffer_init(NULL, buf, 2));
    assert(!labmate_scope_buffer_init(&s, NULL, 2));
    assert(!labmate_scope_buffer_init(&s, buf, 0));
    assert(!labmate_scope_buffer_init(&s, buf, 257));
    s = fresh(buf, 2);
    assert(s.state == LabMateScopeIdle && s.count == 0);
    assert(!labmate_scope_buffer_arm(&s, (LabMateScopeTrigger)99, false));
    assert(s.state == LabMateScopeIdle);
    assert(!labmate_scope_buffer_push_edge(&s, 1, true));
    assert(labmate_scope_buffer_arm(&s, LabMateScopeTriggerRising, false));
    assert(!labmate_scope_buffer_arm(&s, LabMateScopeTriggerRising, false));
    assert(s.state == LabMateScopeArmed);
    assert(labmate_scope_buffer_snapshot(NULL).timebase_error);
    labmate_scope_buffer_stop(NULL);
}

static void test_trigger_rising_and_snapshot(void) {
    LabMateScopeEdge b[4] = {0};
    LabMateScopeBuffer s = fresh(b, 4);
    assert(labmate_scope_buffer_arm(&s, LabMateScopeTriggerRising, true));
    assert(!labmate_scope_buffer_push_edge(&s, 10, false)); /* real falling, not trigger */
    assert(s.count == 0 && s.state == LabMateScopeArmed);
    assert(!labmate_scope_buffer_push_edge(&s, 11, false)); /* duplicate */
    assert(labmate_scope_buffer_push_edge(&s, 20, true));
    assert(s.count == 1 && b[0].tick == 20 && b[0].delta_ticks == 0 && b[0].high);
    assert(labmate_scope_buffer_push_edge(&s, 30, false));
    assert(s.count == 2 && b[1].delta_ticks == 10 && !b[1].high);
    LabMateScopeSnapshot snap = labmate_scope_buffer_snapshot(&s);
    assert(snap.state == LabMateScopeRecording && snap.count == 2 && snap.capacity == 4);
    assert(!snap.overflowed && !snap.timebase_error && snap.dropped_edges == 0);
    labmate_scope_buffer_stop(&s);
    assert(s.state == LabMateScopeStopped);
    assert(!labmate_scope_buffer_push_edge(&s, 35, true));
    assert(s.count == 2);
    assert(labmate_scope_buffer_arm(&s, LabMateScopeTriggerEither, false));
    assert(s.count == 0 && s.dropped_edges == 0 && !s.overflowed);
    assert(labmate_scope_buffer_push_edge(&s, 50, true));
    assert(s.count == 1 && b[0].tick == 50);
}

static void test_falling_trigger(void) {
    LabMateScopeEdge b[2];
    LabMateScopeBuffer s = fresh(b, 2);
    assert(labmate_scope_buffer_arm(&s, LabMateScopeTriggerFalling, false));
    assert(!labmate_scope_buffer_push_edge(&s, 100, true));
    assert(labmate_scope_buffer_push_edge(&s, 110, false));
    assert(!b[0].high && b[0].tick == 110);
}

static void test_wrap_and_ambiguous_timebase(void) {
    LabMateScopeEdge b[3];
    LabMateScopeBuffer s = fresh(b, 3);
    assert(labmate_scope_buffer_arm(&s, LabMateScopeTriggerEither, false));
    assert(labmate_scope_buffer_push_edge(&s, UINT32_MAX - 15U, true));
    assert(labmate_scope_buffer_push_edge(&s, 31U, false));
    assert(b[1].delta_ticks == 47U);
    assert(!labmate_scope_buffer_push_edge(&s, 31U, true));
    assert(s.state == LabMateScopeError && s.timebase_error && s.count == 2);
    assert(s.dropped_edges == 1);
    assert(!labmate_scope_buffer_push_edge(&s, 32U, false));
    labmate_scope_buffer_stop(&s);
    assert(s.state == LabMateScopeStopped && s.timebase_error);
    assert(labmate_scope_buffer_arm(&s, LabMateScopeTriggerEither, false));
    assert(!s.timebase_error && s.count == 0);
    assert(labmate_scope_buffer_push_edge(&s, 1, true));
    assert(!labmate_scope_buffer_push_edge(&s, UINT32_C(0x80000001), false));
    assert(s.timebase_error);
}

static void test_full_overflow_no_buffer_overwrite(void) {
    struct {
        uint32_t before;
        LabMateScopeEdge edges[2];
        uint32_t after;
    } guarded = {.before = 0x12345678, .after = 0x87654321};
    LabMateScopeBuffer s = fresh(guarded.edges, 2);
    assert(labmate_scope_buffer_arm(&s, LabMateScopeTriggerEither, false));
    assert(labmate_scope_buffer_push_edge(&s, 10, true));
    assert(labmate_scope_buffer_push_edge(&s, 20, false));
    assert(!labmate_scope_buffer_push_edge(&s, 30, true));
    assert(s.state == LabMateScopeFull && s.overflowed && s.dropped_edges == 1);
    assert(!labmate_scope_buffer_push_edge(&s, 40, false));
    assert(s.dropped_edges == 2 && s.count == 2);
    assert(!labmate_scope_buffer_push_edge(&s, 45, false));
    assert(s.dropped_edges == 2); /* duplicate ignored */
    assert(!labmate_scope_buffer_arm(&s, LabMateScopeTriggerEither, false)); /* STOP first */
    assert(guarded.before == 0x12345678 && guarded.after == 0x87654321);
    assert(guarded.edges[1].tick == 20);
    s.dropped_edges = UINT32_MAX;
    assert(!labmate_scope_buffer_push_edge(&s, 50, true));
    assert(s.dropped_edges == UINT32_MAX);
    labmate_scope_buffer_stop(&s);
    assert(s.overflowed && s.count == 2 && s.state == LabMateScopeStopped);
}

static void test_full_256_capacity(void) {
    static LabMateScopeEdge b[LABMATE_SCOPE_MAX_EDGES];
    LabMateScopeBuffer s = fresh(b, LABMATE_SCOPE_MAX_EDGES);
    assert(labmate_scope_buffer_arm(&s, LabMateScopeTriggerEither, false));
    for(uint32_t n = 0; n < LABMATE_SCOPE_MAX_EDGES; ++n) {
        assert(labmate_scope_buffer_push_edge(&s, n + 1U, n % 2U == 0U));
    }
    assert(s.count == LABMATE_SCOPE_MAX_EDGES);
    assert(!s.overflowed);
    assert(!labmate_scope_buffer_push_edge(&s, 999U, true));
    assert(s.overflowed && s.dropped_edges == 1);
    assert(b[LABMATE_SCOPE_MAX_EDGES - 1].tick == LABMATE_SCOPE_MAX_EDGES);
}

int main(void) {
    test_validation();
    test_trigger_rising_and_snapshot();
    test_falling_trigger();
    test_wrap_and_ambiguous_timebase();
    test_full_overflow_no_buffer_overwrite();
    test_full_256_capacity();
    puts("LabMate v1.9 bounded real-edge timestamp storage: host tests PASS");
    return 0;
}
