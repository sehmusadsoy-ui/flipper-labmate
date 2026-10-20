#include "labmate_scope_compare.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>

static void capture(LabMateScopeEdge* e, uint16_t cycles,
                    uint32_t start, uint32_t high, uint32_t low) {
    e[0] = (LabMateScopeEdge){.tick = start, .high = true};
    uint32_t now = start;
    for(uint16_t i = 0; i < cycles; ++i) {
        now += high;
        e[2U*i + 1U] = (LabMateScopeEdge){.tick=now,.delta_ticks=high,.high=false};
        now += low;
        e[2U*i + 2U] = (LabMateScopeEdge){.tick=now,.delta_ticks=low,.high=true};
    }
}
static void nominal_and_delta(void) {
    LabMateScopeEdge a[7], b[7];
    capture(a, 3, 50U, 320000U, 320000U); /* 100Hz / 50% */
    capture(b, 3, 50U, 16000U, 48000U);  /* 1kHz / 25% */
    LabMateScopeMetrics ma = labmate_scope_metrics_from_edges(a, 7, 64000000U);
    LabMateScopeMetrics mb = labmate_scope_metrics_from_edges(b, 7, 64000000U);
    assert(ma.status == LabMateScopeMetricsReady && mb.status == LabMateScopeMetricsReady);
    assert(ma.frequency_millihz == 100000 && ma.duty_permille == 500);
    assert(mb.frequency_millihz == 1000000 && mb.duty_permille == 250);
    assert(ma.completed_cycles == 3 && ma.min_period_ticks == 640000 &&
           ma.max_period_ticks == 640000);
    LabMateScopeCompare c = labmate_scope_compare_metrics(&ma,&mb);
    assert(c.comparable && c.frequency_delta_millihz == 900000 &&
           c.duty_delta_permille == -250);
    c = labmate_scope_compare_metrics(&mb, &ma);
    assert(c.comparable && c.frequency_delta_millihz == -900000 &&
           c.duty_delta_permille == 250);
    assert(!labmate_scope_compare_metrics(NULL,&ma).comparable);
}
static void wrap_and_partial(void) {
    LabMateScopeEdge e[6];
    capture(e, 2, UINT32_MAX - 99U, 200U, 800U);
    LabMateScopeMetrics m = labmate_scope_metrics_from_edges(e, 5, 1000000U);
    assert(m.status == LabMateScopeMetricsReady && m.frequency_millihz == 1000000U);
    assert(m.duty_permille == 200U && m.completed_cycles == 2);
    /* Starts at a falling edge. Ignore unmatched LOW half interval. */
    e[0] = (LabMateScopeEdge){.tick=10U,.high=false};
    e[1] = (LabMateScopeEdge){.tick=30U,.delta_ticks=20U,.high=true};
    e[2] = (LabMateScopeEdge){.tick=40U,.delta_ticks=10U,.high=false};
    e[3] = (LabMateScopeEdge){.tick=60U,.delta_ticks=20U,.high=true};
    m = labmate_scope_metrics_from_edges(e,4,3000U);
    assert(m.status==LabMateScopeMetricsReady && m.completed_cycles==1 &&
           m.frequency_millihz==100000U && m.duty_permille==333U);
    m = labmate_scope_metrics_from_edges(e,3,3000U);
    assert(m.status==LabMateScopeMetricsInsufficient);
}
static void invalid_and_timeguard(void) {
    LabMateScopeEdge e[3];
    capture(e,1,0U,10U,20U);
    assert(labmate_scope_metrics_from_edges(e,3,0).status == LabMateScopeMetricsClockInvalid);
    assert(labmate_scope_metrics_from_edges(NULL,3,1000).status == LabMateScopeMetricsInvalid);
    assert(labmate_scope_metrics_from_edges(NULL,0,1000).status == LabMateScopeMetricsInsufficient);
    assert(labmate_scope_metrics_from_edges(e,257,1000).status == LabMateScopeMetricsInvalid);
    e[1].high = true;
    assert(labmate_scope_metrics_from_edges(e,3,1000).status == LabMateScopeMetricsInvalid);
    e[1].high = false;
    e[2].delta_ticks = 0;
    assert(labmate_scope_metrics_from_edges(e,3,1000).status == LabMateScopeMetricsInvalid);
    e[2].delta_ticks = 20;
    /* Individual halves below halfwrap, combined cumulative span above it. */
    e[0] = (LabMateScopeEdge){.tick=0U,.high=true};
    e[1] = (LabMateScopeEdge){.tick=UINT32_C(0x40000000), .delta_ticks=UINT32_C(0x40000000),.high=false};
    e[2] = (LabMateScopeEdge){.tick=UINT32_C(0x80000000), .delta_ticks=UINT32_C(0x40000000),.high=true};
    assert(labmate_scope_metrics_from_edges(e,3,1000).status == LabMateScopeMetricsInvalid);
    LabMateScopeMetrics absent={0};
    assert(!labmate_scope_compare_metrics(&absent,&absent).comparable);
}
static void clock_normalization_and_jitter(void) {
    LabMateScopeEdge a[5], b[5];
    capture(a, 2, 10U, 320000U, 320000U); /* 100 Hz / 50%, 64 MHz */
    capture(b, 2, 10U, 160000U, 160000U); /* same real 100 Hz, 32 MHz */
    LabMateScopeMetrics ma = labmate_scope_metrics_from_edges(a, 5, 64000000U);
    LabMateScopeMetrics mb = labmate_scope_metrics_from_edges(b, 5, 32000000U);
    LabMateScopeCompare cmp = labmate_scope_compare_metrics(&ma, &mb);
    assert(cmp.comparable && cmp.frequency_delta_millihz == 0 &&
           cmp.duty_delta_permille == 0);
    b[3].tick += 10000U; /* second HIGH duration is longer */
    b[3].delta_ticks += 10000U;
    b[4].delta_ticks -= 10000U; /* second LOW duration is shorter */
    mb = labmate_scope_metrics_from_edges(b, 5, 32000000U);
    assert(mb.status == LabMateScopeMetricsReady && mb.completed_cycles == 2);
    assert(mb.frequency_millihz == 100000U && mb.duty_permille == 516U);
    assert(mb.min_period_ticks == 320000U && mb.max_period_ticks == 320000U);
}
static void saturated_bounds(void) {
    LabMateScopeEdge e[255];
    capture(e,127,100U,1U,1U);
    LabMateScopeMetrics m = labmate_scope_metrics_from_edges(e,255,64000000U);
    assert(m.status == LabMateScopeMetricsReady);
    assert(m.completed_cycles==127 && m.frequency_millihz==32000000000ULL);
    assert(m.duty_permille==500 && m.min_period_ticks==2 && m.max_period_ticks==2);
}
int main(void) {
    nominal_and_delta(); wrap_and_partial(); invalid_and_timeguard(); saturated_bounds();
    clock_normalization_and_jitter();
    puts("v1.9 Signal Compare sequential actual 3.3V PC1 captures PASS");
    return 0;
}
