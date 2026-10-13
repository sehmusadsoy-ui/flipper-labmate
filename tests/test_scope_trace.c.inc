/* Host-only: 1-channel digital event trace; no GPIO, no timing calibration. */
#include "labmate_scope_trace.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static void test_invalid_starts_and_stale_generations(void) {
    LabMateScopeTrace t;
    LabMateScopeEvent event = {0};
    uint32_t gen = 765U;
    labmate_scope_trace_init(&t);
    assert(!labmate_scope_trace_is_active(&t));
    assert(!labmate_scope_trace_start(NULL, LabMateScopeTriggerImmediate, 0, 0, &gen));
    assert(!labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 0, 0, NULL));
    assert(!labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 2, 0, &gen));
    assert(!labmate_scope_trace_start(&t, (LabMateScopeTrigger)99, 0, 0, &gen));
    assert(gen == 765U && t.event_count == 0U && t.generation == 0U);
    assert(!labmate_scope_trace_event_at(&t, 0U, &event));
    assert(!labmate_scope_trace_event_at(NULL, 0U, &event));
    assert(!labmate_scope_trace_event_at(&t, 0U, NULL));

    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 0U, 100U, &gen));
    assert(gen == 1U && labmate_scope_trace_is_active(&t));
    assert(t.state == LabMateScopeRecording && t.event_count == 1U);
    assert(labmate_scope_trace_event_at(&t, 0U, &event));
    assert(event.offset_ticks == 0U && event.level == 0U);
    assert(!labmate_scope_trace_event_at(&t, 1U, &event));
    assert(!labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 1U, 110U, &gen));
    assert(labmate_scope_trace_feed(&t, gen + 1U, 101U, 1U) == LabMateScopeFeedStale);
    assert(t.event_count == 1U && t.last_tick == 100U);
    assert(!labmate_scope_trace_stop(&t, gen + 1U));
    assert(labmate_scope_trace_feed(NULL, gen, 101U, 1U) == LabMateScopeFeedInactive);
    assert(labmate_scope_trace_feed(&t, gen, 100U, 0U) == LabMateScopeFeedIgnored);
    assert(labmate_scope_trace_feed(&t, gen, 101U, 0U) == LabMateScopeFeedIgnored);
    assert(t.event_count == 1U && t.elapsed_ticks == 1U);
    assert(labmate_scope_trace_feed(&t, gen, 105U, 1U) == LabMateScopeFeedRecorded);
    assert(t.event_count == 2U);
    assert(labmate_scope_trace_event_at(&t, 1U, &event));
    assert(event.offset_ticks == 5U && event.level == 1U);
    assert(labmate_scope_trace_stop(&t, gen));
    assert(!labmate_scope_trace_is_active(&t));
    assert(t.state == LabMateScopeStopped && t.event_count == 2U);
    assert(!labmate_scope_trace_stop(&t, gen));
    assert(labmate_scope_trace_feed(&t, gen, 106U, 0U) == LabMateScopeFeedInactive);
    uint32_t next=0U;
    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 1U, 110U, &next));
    assert(next == gen + 1U && t.event_count == 1U && t.events[0].level == 1U);
    assert(labmate_scope_trace_feed(&t, gen, 111U, 0U) == LabMateScopeFeedStale);
    assert(t.event_count == 1U);
}

static void test_edge_trigger_and_no_fake_pretrigger(void) {
    LabMateScopeTrace t;
    uint32_t gen;
    labmate_scope_trace_init(&t);
    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerRising, 1U, 100U, &gen));
    assert(t.state == LabMateScopeArmed && t.event_count == 0U);
    assert(labmate_scope_trace_feed(&t, gen, 101U, 0U) == LabMateScopeFeedIgnored);
    assert(t.event_count == 0U);
    assert(labmate_scope_trace_feed(&t, gen, 102U, 1U) == LabMateScopeFeedTriggered);
    assert(t.state == LabMateScopeRecording && t.event_count == 1U);
    assert(t.events[0].offset_ticks == 0U && t.events[0].level == 1U);
    assert(labmate_scope_trace_feed(&t, gen, 107U, 0U) == LabMateScopeFeedRecorded);
    assert(t.events[1].offset_ticks == 5U && t.events[1].level == 0U);
    assert(labmate_scope_trace_stop(&t, gen));
    assert(t.state == LabMateScopeStopped);
    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerFalling, 0U, 0U, &gen));
    assert(labmate_scope_trace_feed(&t, gen, 1U, 1U) == LabMateScopeFeedIgnored);
    assert(labmate_scope_trace_feed(&t, gen, 3U, 0U) == LabMateScopeFeedTriggered);
    assert(t.events[0].level == 0U && t.events[0].offset_ticks == 0U);
    assert(labmate_scope_trace_stop(&t, gen));
    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerEither, 0U, 0U, &gen));
    assert(labmate_scope_trace_feed(&t, gen, 100U, 0U) == LabMateScopeFeedIgnored);
    assert(labmate_scope_trace_feed(&t, gen, 101U, 1U) == LabMateScopeFeedTriggered);
    assert(labmate_scope_trace_stop(&t, gen));
    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerRising, 0U, 10U, &gen));
    assert(labmate_scope_trace_feed(&t, gen, 11U, 0U) == LabMateScopeFeedIgnored);
    assert(labmate_scope_trace_stop(&t, gen));
    assert(t.state == LabMateScopeStopped && t.event_count == 0U);
}

static void test_wrap_and_clock_failures(void) {
    LabMateScopeTrace t;
    uint32_t gen;
    labmate_scope_trace_init(&t);
    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 0U, UINT32_MAX-3U, &gen));
    assert(labmate_scope_trace_feed(&t, gen, UINT32_MAX, 1U) == LabMateScopeFeedRecorded);
    assert(t.events[1].offset_ticks == 3U);
    assert(labmate_scope_trace_feed(&t, gen, 3U, 0U) == LabMateScopeFeedRecorded);
    assert(t.events[2].offset_ticks == 7U && t.events[2].level == 0U);
    assert(labmate_scope_trace_stop(&t, gen));

    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 0U, 10U, &gen));
    assert(labmate_scope_trace_feed(&t, gen, 11U, 1U) == LabMateScopeFeedRecorded);
    assert(labmate_scope_trace_feed(&t, gen, 10U, 0U) == LabMateScopeFeedFault);
    assert(t.state == LabMateScopeFault && t.fault_reason == LabMateScopeFaultClock);
    assert(t.event_count == 2U);
    assert(!labmate_scope_trace_stop(&t, gen));
    assert(labmate_scope_trace_feed(&t, gen, 12U, 0U) == LabMateScopeFeedInactive);

    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 0U, 10U, &gen));
    assert(labmate_scope_trace_feed(&t, gen, 10U, 1U) == LabMateScopeFeedFault);
    assert(t.fault_reason == LabMateScopeFaultClock);

    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerRising, 0U, 10U, &gen));
    assert(labmate_scope_trace_feed(&t, gen, 11U, 2U) == LabMateScopeFeedFault);
    assert(t.fault_reason == LabMateScopeFaultInvalidLevel);
    assert(t.event_count == 0U);
    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 0U, 0U, &gen));
    assert(labmate_scope_trace_feed(&t, gen, LABMATE_SCOPE_MAX_SPAN_TICKS, 0U) ==
           LabMateScopeFeedIgnored);
    assert(labmate_scope_trace_feed(&t, gen, LABMATE_SCOPE_MAX_SPAN_TICKS+1U, 0U) ==
           LabMateScopeFeedFault);
    assert(t.fault_reason == LabMateScopeFaultSpan);
    assert(t.events[0].offset_ticks == 0U && t.event_count == 1U);

    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 0U, 0U, &gen));
    assert(labmate_scope_trace_feed(&t, gen, UINT32_C(0x80000000), 1U) ==
           LabMateScopeFeedFault);
    assert(t.fault_reason == LabMateScopeFaultClock);
}

static void test_buffer_full_without_overwrite(void) {
    LabMateScopeTrace t;
    uint32_t gen;
    labmate_scope_trace_init(&t);
    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 0U, 1000U, &gen));
    assert(sizeof(t.events) <= 1024U);
    for(uint32_t i = 1U; i < LABMATE_SCOPE_MAX_EVENTS; ++i) {
        assert(labmate_scope_trace_feed(&t, gen, 1000U+i, (uint8_t)(i & 1U)) ==
               LabMateScopeFeedRecorded);
    }
    assert(t.state == LabMateScopeRecording && t.event_count == 128U);
    assert(t.events[127U].offset_ticks == 127U && t.events[127U].level == 1U);
    assert(t.missed_lower_bound == 0U);
    assert(labmate_scope_trace_feed(&t, gen, 1128U, 0U) == LabMateScopeFeedOverflow);
    assert(t.state == LabMateScopeOverflow && t.missed_lower_bound == 1U);
    assert(t.event_count == 128U && t.events[127U].offset_ticks == 127U);
    assert(!labmate_scope_trace_stop(&t, gen));
    assert(labmate_scope_trace_feed(&t, gen, 1129U, 1U) == LabMateScopeFeedInactive);
    assert(t.missed_lower_bound == 1U); /* LOWER BOUND, not false exact total. */
    uint32_t next;
    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 1U, 2000U, &next));
    assert(next != gen && t.event_count == 1U && t.missed_lower_bound == 0U);
}

static void test_generation_saturation_and_retained_final_state(void) {
    LabMateScopeTrace t;
    labmate_scope_trace_init(&t);
    t.generation = UINT32_MAX;
    uint32_t out=44U;
    assert(!labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 0U, 0U, &out));
    assert(out == 44U && t.state == LabMateScopeIdle);
    labmate_scope_trace_init(&t);
    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerRising, 0U, 0U, &out));
    assert(labmate_scope_trace_feed(&t, out, 1U, 0U) == LabMateScopeFeedIgnored);
    assert(t.state == LabMateScopeArmed && t.event_count == 0U);
    assert(labmate_scope_trace_stop(&t, out));
    assert(t.event_count == 0U && t.state == LabMateScopeStopped);
}

int main(void) {
    test_invalid_starts_and_stale_generations();
    test_edge_trigger_and_no_fake_pretrigger();
    test_wrap_and_clock_failures();
    test_buffer_full_without_overwrite();
    test_generation_saturation_and_retained_final_state();
    puts("v1.9 scope HOST: 128-event cap, triggers, stale tokens, wrap, clock faults, overflow PASS");
    return 0;
}
