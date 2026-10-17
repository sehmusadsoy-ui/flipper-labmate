#include "labmate_scope_timeguard.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

static LabMateScopeSnapshot snap(LabMateScopeState state, uint16_t n) {
    return (LabMateScopeSnapshot){.state = state, .capacity = 4, .count = n};
}
static LabMateScopeTimeguard fresh(uint32_t t0) {
    LabMateScopeTimeguard g;
    assert(labmate_scope_timeguard_init(&g, t0, 100, 50, 500, 20));
    return g;
}
static void test_init_validation(void) {
    LabMateScopeTimeguard g;
    assert(!labmate_scope_timeguard_init(NULL, 0, 100, 50, 500, 20));
    assert(!labmate_scope_timeguard_init(&g, 0, 0, 50, 500, 20));
    assert(!labmate_scope_timeguard_init(&g, 0, 100, 0, 500, 20));
    assert(!labmate_scope_timeguard_init(&g, 0, 100, 50, 0, 20));
    assert(!labmate_scope_timeguard_init(&g, 0, 100, 50, 500, 0));
    assert(!labmate_scope_timeguard_init(&g, 0, 501, 50, 500, 20));
    assert(!labmate_scope_timeguard_init(&g, 0, 100, 501, 500, 20));
    assert(!labmate_scope_timeguard_init(&g, 0, 100, 50, 500, 51));
    assert(!labmate_scope_timeguard_init(&g, 0, 100, 50, 500, 0x80000000U));
    assert(!labmate_scope_timeguard_init(&g, 0, 100, 50, 0x80000000U, 10));
    assert(labmate_scope_timeguard_poll(NULL, 0, snap(LabMateScopeArmed, 0)) == LabMateScopeGuardInvalid);
    g = (LabMateScopeTimeguard){0};
    assert(labmate_scope_timeguard_poll(&g, 0, snap(LabMateScopeArmed, 0)) == LabMateScopeGuardInvalid);
}
static void test_no_trigger_not_fake_signal(void) {
    LabMateScopeTimeguard g = fresh(10);
    for(uint32_t t = 10; t <= 110; t += 10) {
        LabMateScopeGuardResult r = labmate_scope_timeguard_poll(&g, t, snap(LabMateScopeArmed, 0));
        assert(r == (t < 110 ? LabMateScopeGuardRunning : LabMateScopeGuardNoTrigger));
    }
    assert(g.elapsed_ms == 100 && g.previous_edge_count == 0);
    assert(labmate_scope_timeguard_poll(&g, 111, snap(LabMateScopeRecording, 3)) == LabMateScopeGuardNoTrigger);
}
static void test_stalled_after_real_edges(void) {
    LabMateScopeTimeguard g = fresh(0);
    assert(labmate_scope_timeguard_poll(&g, 10, snap(LabMateScopeArmed, 0)) == LabMateScopeGuardRunning);
    assert(labmate_scope_timeguard_poll(&g, 20, snap(LabMateScopeRecording, 1)) == LabMateScopeGuardRunning);
    assert(labmate_scope_timeguard_poll(&g, 40, snap(LabMateScopeRecording, 1)) == LabMateScopeGuardRunning);
    assert(labmate_scope_timeguard_poll(&g, 50, snap(LabMateScopeRecording, 2)) == LabMateScopeGuardRunning);
    assert(labmate_scope_timeguard_poll(&g, 70, snap(LabMateScopeRecording, 2)) == LabMateScopeGuardRunning);
    assert(labmate_scope_timeguard_poll(&g, 90, snap(LabMateScopeRecording, 2)) == LabMateScopeGuardRunning);
    assert(labmate_scope_timeguard_poll(&g, 100, snap(LabMateScopeRecording, 2)) == LabMateScopeGuardQuiet);
    assert(g.quiet_ms == 50);
}
static void test_clock_gap_and_wrap(void) {
    LabMateScopeTimeguard g = fresh(UINT32_MAX - 5U);
    assert(labmate_scope_timeguard_poll(&g, 4U, snap(LabMateScopeArmed, 0)) == LabMateScopeGuardRunning);
    assert(g.elapsed_ms == 10);
    assert(labmate_scope_timeguard_poll(&g, 40U, snap(LabMateScopeArmed, 0)) == LabMateScopeGuardClockUnsafe);
    assert(g.elapsed_ms == 10); /* failed poll does not invent elapsed data */
    g = fresh(100U);
    assert(labmate_scope_timeguard_poll(&g, 99U, snap(LabMateScopeArmed, 0)) == LabMateScopeGuardClockUnsafe);
}
static void test_max_capture_duration(void) {
    LabMateScopeTimeguard g;
    assert(labmate_scope_timeguard_init(&g, 0, 100, 500, 500, 20));
    for(uint32_t t = 10; t <= 500; t += 10) {
        /* An active input with no new edges eventually hits session bound.
         * The longer quiet timeout intentionally cannot fire earlier. */
        LabMateScopeSnapshot s = snap(LabMateScopeRecording, 1);
        LabMateScopeGuardResult r = labmate_scope_timeguard_poll(&g, t, s);
        assert(r == (t < 500 ? LabMateScopeGuardRunning : LabMateScopeGuardDurationLimit));
    }
}
static void test_full_fault_stopped_and_invalid(void) {
    LabMateScopeTimeguard g = fresh(0);
    LabMateScopeSnapshot s = snap(LabMateScopeFull, 4);
    s.overflowed = true;
    assert(labmate_scope_timeguard_poll(&g, 10, s) == LabMateScopeGuardFull);
    g = fresh(0);
    s = snap(LabMateScopeRecording, 2); s.timebase_error = true;
    assert(labmate_scope_timeguard_poll(&g, 10, s) == LabMateScopeGuardCaptureError);
    g = fresh(0);
    assert(labmate_scope_timeguard_poll(&g, 10, snap(LabMateScopeStopped, 2)) == LabMateScopeGuardStopped);
    g = fresh(0);
    assert(labmate_scope_timeguard_poll(&g, 10, snap(LabMateScopeRecording, 0)) == LabMateScopeGuardInvalid);
    g = fresh(0);
    assert(labmate_scope_timeguard_poll(&g, 10, snap(LabMateScopeIdle, 0)) == LabMateScopeGuardInvalid);
    g = fresh(0);
    s = snap(LabMateScopeArmed, 0); s.capacity = 0;
    assert(labmate_scope_timeguard_poll(&g, 10, s) == LabMateScopeGuardInvalid);
    g = fresh(0);
    assert(labmate_scope_timeguard_poll(&g, 10, snap(LabMateScopeRecording, 2)) == LabMateScopeGuardRunning);
    assert(labmate_scope_timeguard_poll(&g, 20, snap(LabMateScopeRecording, 1)) == LabMateScopeGuardInvalid);
}
static void test_real_buffer_integration(void) {
    LabMateScopeEdge edge_storage[4];
    LabMateScopeBuffer scope;
    assert(labmate_scope_buffer_init(&scope, edge_storage, 4));
    assert(labmate_scope_buffer_arm(&scope, LabMateScopeTriggerEither, false));
    LabMateScopeTimeguard guard = fresh(1000);
    assert(labmate_scope_timeguard_poll(&guard, 1010, labmate_scope_buffer_snapshot(&scope))
           == LabMateScopeGuardRunning);
    assert(labmate_scope_buffer_push_edge(&scope, 1234U, true));
    assert(labmate_scope_timeguard_poll(&guard, 1020, labmate_scope_buffer_snapshot(&scope))
           == LabMateScopeGuardRunning);
    assert(labmate_scope_buffer_push_edge(&scope, 1250U, false));
    assert(labmate_scope_timeguard_poll(&guard, 1030, labmate_scope_buffer_snapshot(&scope))
           == LabMateScopeGuardRunning);
    assert(labmate_scope_timeguard_poll(&guard, 1050, labmate_scope_buffer_snapshot(&scope))
           == LabMateScopeGuardRunning);
    assert(labmate_scope_timeguard_poll(&guard, 1070, labmate_scope_buffer_snapshot(&scope))
           == LabMateScopeGuardRunning);
    assert(labmate_scope_timeguard_poll(&guard, 1080, labmate_scope_buffer_snapshot(&scope))
           == LabMateScopeGuardQuiet);
    assert(scope.state == LabMateScopeRecording && scope.count == 2);
    assert(edge_storage[0].tick == 1234U && edge_storage[1].tick == 1250U);
    labmate_scope_buffer_stop(&scope); /* real driver would first detach IRQ */
    assert(scope.state == LabMateScopeStopped && scope.count == 2);
}

int main(void) {
    test_init_validation();
    test_no_trigger_not_fake_signal();
    test_stalled_after_real_edges();
    test_clock_gap_and_wrap();
    test_max_capture_duration();
    test_full_fault_stopped_and_invalid();
    test_real_buffer_integration();
    puts("LabMate v1.9 scope no-trigger/quiet/duration/timebase host PASS");
    return 0;
}
