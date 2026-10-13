/* Native host-only tests: 120-column projection, NOT Flipper Canvas/IRQ. */
#include "labmate_scope_project.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void test_edges_scale_and_no_synthetic_pulses(void) {
    LabMateScopeTrace t;
    LabMateScopeProjection p;
    uint32_t gen;
    labmate_scope_trace_init(&t);
    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 0U, 100U, &gen));
    assert(labmate_scope_trace_feed(&t, gen, 110U, 1U) == LabMateScopeFeedRecorded);
    assert(labmate_scope_trace_feed(&t, gen, 120U, 0U) == LabMateScopeFeedRecorded);
    assert(labmate_scope_trace_feed(&t, gen, 130U, 1U) == LabMateScopeFeedRecorded);
    assert(labmate_scope_trace_feed(&t, gen, 140U, 1U) == LabMateScopeFeedIgnored);
    assert(t.event_count == 4U && t.elapsed_ticks == 40U);
    assert(labmate_scope_project(&t, 0U, 40U, &p));
    assert(p.state == LabMateScopeViewTrace && p.has_waveform);
    assert(!p.left_cropped && !p.right_cropped);
    assert(p.dense_columns == 0U);
    assert(p.columns[0].entering_level == 0U && p.columns[0].leaving_level == 0U);
    assert(p.columns[28].leaving_level == 0U);
    assert(p.columns[29].entering_level == 0U &&
           p.columns[29].leaving_level == 1U &&
           p.columns[29].transitions == 1U);
    assert(p.columns[30].entering_level == 1U && p.columns[30].transitions == 0U);
    assert(p.columns[59].entering_level == 1U &&
           p.columns[59].leaving_level == 0U && p.columns[59].transitions == 1U);
    assert(p.columns[89].entering_level == 0U &&
           p.columns[89].leaving_level == 1U && p.columns[89].transitions == 1U);
    assert(p.columns[119].entering_level == 1U &&
           p.columns[119].leaving_level == 1U && p.columns[119].transitions == 0U);
    assert(p.columns[5].entering_level == p.columns[5].leaving_level);
    assert(p.columns[5].transitions == 0U);
    assert(labmate_scope_trace_stop(&t, gen));
    assert(labmate_scope_project(&t, 0U, 40U, &p) && p.has_waveform);
}

static void test_dense_columns_never_render_fake_clean_pulse(void) {
    LabMateScopeTrace t;
    LabMateScopeProjection p;
    uint32_t gen;
    labmate_scope_trace_init(&t);
    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 0U, 0U, &gen));
    for(uint32_t i=1U; i<=5U; ++i) {
        assert(labmate_scope_trace_feed(&t, gen, i, (uint8_t)(i & 1U)) ==
               LabMateScopeFeedRecorded);
    }
    assert(labmate_scope_trace_feed(&t, gen, 1000U, 1U) == LabMateScopeFeedIgnored);
    assert(labmate_scope_project(&t, 0U, 1000U, &p));
    assert(p.columns[0].transitions == 5U);
    assert(p.columns[0].entering_level == 0U && p.columns[0].leaving_level == 1U);
    assert(p.dense_columns == 1U);
    for(unsigned x=1U; x<LABMATE_SCOPE_GRAPH_COLUMNS; ++x) {
        assert(p.columns[x].transitions == 0U);
        assert(p.columns[x].entering_level == 1U && p.columns[x].leaving_level == 1U);
    }
}

static void test_crop_and_exact_right_endpoint(void) {
    LabMateScopeTrace t;
    LabMateScopeProjection p;
    uint32_t gen;
    labmate_scope_trace_init(&t);
    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 0U, 100U, &gen));
    assert(labmate_scope_trace_feed(&t, gen, 110U, 1U) == LabMateScopeFeedRecorded);
    assert(labmate_scope_trace_feed(&t, gen, 120U, 0U) == LabMateScopeFeedRecorded);
    assert(labmate_scope_trace_feed(&t, gen, 140U, 0U) == LabMateScopeFeedIgnored);

    assert(labmate_scope_project(&t, 15U, 40U, &p));
    assert(p.left_cropped && !p.right_cropped);
    assert(p.columns[0].entering_level == 1U && p.columns[0].transitions == 0U);
    assert(p.columns[23].transitions == 1U);
    assert(p.columns[23].entering_level == 1U && p.columns[23].leaving_level == 0U);

    assert(labmate_scope_project(&t, 0U, 20U, &p));
    assert(!p.left_cropped && p.right_cropped);
    assert(p.columns[119].transitions == 1U);
    assert(p.columns[119].leaving_level == 0U);
    assert(labmate_scope_project(&t, 20U, 40U, &p));
    assert(p.left_cropped && p.columns[0].entering_level == 0U);
    assert(p.columns[0].transitions == 0U); /* boundary transition not redrawn */
}

static void test_no_trigger_no_span_fault_and_invalid(void) {
    LabMateScopeTrace t;
    LabMateScopeProjection p;
    uint32_t gen;
    labmate_scope_trace_init(&t);
    assert(!labmate_scope_project(NULL, 0U, 2U, &p));
    assert(p.state == LabMateScopeViewInvalid && !p.has_waveform);
    assert(!labmate_scope_project(&t, 0U, 2U, NULL));
    assert(!labmate_scope_project(&t, 5U, 5U, &p));
    assert(!labmate_scope_project(&t, 7U, 5U, &p));
    assert(p.state == LabMateScopeViewInvalid && !p.has_waveform);

    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerRising, 0U, 100U, &gen));
    assert(labmate_scope_project(&t, 0U, 10U, &p));
    assert(p.state == LabMateScopeViewWaitingTrigger && !p.has_waveform);
    assert(labmate_scope_trace_stop(&t, gen));
    assert(labmate_scope_project(&t, 0U, 10U, &p));
    assert(p.state == LabMateScopeViewNotTriggered && !p.has_waveform);

    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 0U, 100U, &gen));
    assert(labmate_scope_project(&t, 0U, 10U, &p));
    assert(p.state == LabMateScopeViewNoSpan && !p.has_waveform);
    assert(labmate_scope_trace_feed(&t, gen, 110U, 1U) == LabMateScopeFeedRecorded);
    assert(!labmate_scope_project(&t, 0U, 11U, &p));
    assert(p.state == LabMateScopeViewInvalid && !p.has_waveform);
    assert(labmate_scope_project(&t, 0U, 10U, &p));
    assert(p.state == LabMateScopeViewTrace);
    assert(labmate_scope_trace_feed(&t, gen, 110U, 0U) == LabMateScopeFeedFault);
    assert(labmate_scope_project(&t, 0U, 10U, &p));
    assert(p.state == LabMateScopeViewFault && p.has_waveform);
    assert(!labmate_scope_project(&t, 0U, 11U, &p));

    /* Corrupted model output may not be projected as real waveform. */
    t.events[1].offset_ticks = 0U;
    assert(!labmate_scope_project(&t, 0U, 10U, &p));
    t.events[1].offset_ticks = 10U;
    t.events[1].level = 0U;
    assert(!labmate_scope_project(&t, 0U, 10U, &p));
    t.events[1].level = 2U;
    assert(!labmate_scope_project(&t, 0U, 10U, &p));
    t.event_count = LABMATE_SCOPE_MAX_EVENTS + 1U;
    assert(!labmate_scope_project(&t, 0U, 10U, &p));
}

static void test_overflow_unknown_tail_never_drawn(void) {
    LabMateScopeTrace t;
    LabMateScopeProjection p;
    uint32_t gen;
    labmate_scope_trace_init(&t);
    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 0U, 100U, &gen));
    for(uint32_t i=1U; i<LABMATE_SCOPE_MAX_EVENTS; ++i) {
        assert(labmate_scope_trace_feed(&t, gen, 100U+i, (uint8_t)(i & 1U)) ==
               LabMateScopeFeedRecorded);
    }
    assert(t.event_count == LABMATE_SCOPE_MAX_EVENTS);
    assert(labmate_scope_trace_feed(&t, gen, 228U, 0U) == LabMateScopeFeedOverflow);
    assert(t.elapsed_ticks == 128U && t.events[127].offset_ticks == 127U);
    /* 128th tick includes omitted transition, so that tick is UNKNOWN. */
    assert(!labmate_scope_project(&t, 0U, 128U, &p));
    assert(p.state == LabMateScopeViewInvalid);
    assert(labmate_scope_project(&t, 0U, 127U, &p));
    assert(p.state == LabMateScopeViewOverflow && p.has_waveform);
    assert(p.right_cropped && p.columns[119].transitions == 1U);
    assert(p.columns[119].leaving_level == 1U);
}

static void test_large_tick_span_uses_64_bit_math(void) {
    LabMateScopeTrace t;
    LabMateScopeProjection p;
    uint32_t gen;
    labmate_scope_trace_init(&t);
    assert(labmate_scope_trace_start(&t, LabMateScopeTriggerImmediate, 0U, 0U, &gen));
    assert(labmate_scope_trace_feed(
        &t, gen, LABMATE_SCOPE_MAX_SPAN_TICKS, 1U) == LabMateScopeFeedRecorded);
    assert(labmate_scope_project(&t, 0U, LABMATE_SCOPE_MAX_SPAN_TICKS, &p));
    assert(p.columns[119].transitions == 1U);
    assert(p.columns[119].leaving_level == 1U);
    assert(p.dense_columns == 0U);
    assert(sizeof(p.columns) <= 360U); /* bounded projection RAM */
}

int main(void) {
    test_edges_scale_and_no_synthetic_pulses();
    test_dense_columns_never_render_fake_clean_pulse();
    test_crop_and_exact_right_endpoint();
    test_no_trigger_no_span_fault_and_invalid();
    test_overflow_unknown_tail_never_drawn();
    test_large_tick_span_uses_64_bit_math();
    puts("v1.9 scope L1 HOST: 120 columns, dense edges, cropped windows, honest overflow/fault PASS");
    return 0;
}
