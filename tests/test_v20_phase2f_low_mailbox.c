/* Host test of the exact production static helper, extracted by shell runner. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include "labmate_low_mailbox_audit.h"

typedef struct {
    volatile bool frequency_irq_new_period;
    volatile uint32_t frequency_irq_period_cycles;
    /* Phase3D copies native IRQ provenance in the same critical section. */
    volatile uint32_t frequency_irq_edges;
    volatile uint32_t frequency_irq_last_tick;
    LabMateLowMailboxAudit frequency_low_mailbox_audit;
    LabMateLowMailboxObservation frequency_low_last_observation;
} LabMateApp;
static LabMateApp* active;
static bool locked, deferred;
static uint32_t deferred_value;
static bool inject_before_enter, inject_after_exit;
static uint32_t inject_value;
static unsigned enters, exits, published, doctor_notes;
static uint32_t last_critical_edges, last_critical_tick;
static uint32_t last_doctor_edges, last_doctor_tick;

/* The production Phase3D adapter is not compiled by this Phase2F fixture.
 * Verify that the extracted helper passes one coherent IRQ snapshot AFTER
 * unlocking, even if another IRQ publishes at host_exit().
 */
static void labmate_doctor_frequency_note_low(
    LabMateApp* app, const LabMateLowMailboxObservation* observation,
    uint32_t edges, uint32_t tick) {
    assert(app == active && !locked);
    assert(observation && observation->has_period);
    assert(edges == last_critical_edges && tick == last_critical_tick);
    assert(edges >= observation->publications * 2U);
    last_doctor_edges = edges;
    last_doctor_tick = tick;
    ++doctor_notes;
}
static void irq_publish_now(uint32_t value) {
    assert(active && !locked);
    labmate_low_mailbox_publish(&active->frequency_low_mailbox_audit,
                                 active->frequency_irq_new_period);
    active->frequency_irq_period_cycles = value;
    active->frequency_irq_new_period = true;
    /* Each mock publication contains a complete two-edge period. */
    active->frequency_irq_edges += 2U;
    ++active->frequency_irq_last_tick;
    ++published;
}
static void irq_publish(uint32_t value) {
    if(locked) { deferred=true; deferred_value=value; }
    else irq_publish_now(value);
}
static void host_enter(void) {
    assert(!locked);
    if(inject_before_enter) {
        inject_before_enter=false;
        irq_publish_now(inject_value);
    }
    locked=true;
    ++enters;
}
static void host_exit(void) {
    assert(locked);
    /* Snapshot before exit injection: both fields must remain coherent. */
    last_critical_edges = active->frequency_irq_edges;
    last_critical_tick = active->frequency_irq_last_tick;
    locked=false;
    ++exits;
    if(deferred) { deferred=false; irq_publish_now(deferred_value); }
    if(inject_after_exit) {
        inject_after_exit=false;
        irq_publish_now(inject_value);
    }
}
#define FURI_CRITICAL_ENTER() host_enter()
#define FURI_CRITICAL_EXIT() host_exit()
#include "take_period.inc"

int main(void) {
    unsigned scenarios=0;
    LabMateApp app={0};
    active=&app;
    uint32_t result=555;
    assert(!labmate_frequency_low_take_period(NULL,&result));
    assert(!labmate_frequency_low_take_period(&app,NULL));
    assert(result==555 && enters==0 && exits==0 && doctor_notes==0);scenarios+=2;
    assert(!labmate_frequency_low_take_period(&app,&result));
    assert(result==555 && !app.frequency_irq_new_period && doctor_notes==0);scenarios++;
    irq_publish(100);
    assert(labmate_frequency_low_take_period(&app,&result));
    assert(result==100 && !app.frequency_irq_new_period);scenarios++;
    // IRQ arrives before entering the critical section: newest period is consumed.
    inject_before_enter=true;inject_value=200;
    assert(labmate_frequency_low_take_period(&app,&result));
    assert(result==200 && !app.frequency_irq_new_period);scenarios++;
    // IRQ published at critical exit remains pending for next update, not lost.
    irq_publish(300); inject_after_exit=true;inject_value=400;
    assert(labmate_frequency_low_take_period(&app,&result));
    assert(result==300 && app.frequency_irq_new_period && app.frequency_irq_period_cycles==400);
    assert(app.frequency_low_last_observation.period_cycles==300U);
    assert(app.frequency_low_last_observation.publications==3U);
    assert(app.frequency_low_last_observation.overwrites==0U);
    /* The after-exit IRQ (400) cannot contaminate the Doctor's
     * pre-exit period (300) or its copied counter/tick.
     */
    assert(last_doctor_edges + 2U == app.frequency_irq_edges);
    assert(last_doctor_tick + 1U == app.frequency_irq_last_tick);scenarios++;
    assert(labmate_frequency_low_take_period(&app,&result));
    assert(result==400 && !app.frequency_irq_new_period);
    assert(app.frequency_low_last_observation.period_cycles==400U);
    assert(app.frequency_low_last_observation.overwrites==0U);scenarios++;
    // Two actual ISR publications while the single mailbox is unread.
    irq_publish(410);irq_publish(420);
    assert(labmate_frequency_low_take_period(&app,&result));
    assert(result==420U && app.frequency_low_last_observation.has_period);
    assert(app.frequency_low_last_observation.publications==6U);
    assert(app.frequency_low_last_observation.overwrites==1U);scenarios++;
    // Empty mailbox, IRQ on exit: subsequent poll must pick it up.
    inject_after_exit=true;inject_value=500;
    const unsigned notes_before_empty = doctor_notes;
    assert(!labmate_frequency_low_take_period(&app,&result));
    assert(result==420 && app.frequency_irq_new_period &&
           doctor_notes==notes_before_empty);scenarios++;
    assert(labmate_frequency_low_take_period(&app,&result));
    assert(result==500 && !app.frequency_irq_new_period);scenarios++;
    // Valid pending zero period: caller filters it as before; ack is atomic.
    irq_publish(0);
    assert(labmate_frequency_low_take_period(&app,&result));
    assert(result==0 && !app.frequency_irq_new_period);scenarios++;
    for(uint32_t i=1;i<=4096;i++) {
        irq_publish(i);
        if((i&1U)==0U) { inject_after_exit=true;inject_value=i+9000; }
        assert(labmate_frequency_low_take_period(&app,&result));
        assert(result==i);
        if((i&1U)==0U) {
            assert(app.frequency_irq_new_period);
            assert(labmate_frequency_low_take_period(&app,&result));
            assert(result==i+9000 && !app.frequency_irq_new_period);
        } else assert(!app.frequency_irq_new_period);
        assert(enters==exits && !locked);
        assert(app.frequency_low_last_observation.publications <=
               app.frequency_low_mailbox_audit.publications);
        scenarios++;
    }
    assert(!deferred && enters==exits && enters>0 && published>4000);
    assert(doctor_notes==6151U);
    assert(last_doctor_edges==app.frequency_irq_edges);
    assert(last_doctor_tick==app.frequency_irq_last_tick);
    printf("Phase2F LOW atomic IRQ mailbox PASS: %u deterministic states\n",scenarios);
    return scenarios==4107?0:1;
}
