/* Host test of the exact production static helper, extracted by shell runner. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

typedef struct {
    volatile bool frequency_irq_new_period;
    volatile uint32_t frequency_irq_period_cycles;
} LabMateApp;
static LabMateApp* active;
static bool locked, deferred;
static uint32_t deferred_value;
static bool inject_before_enter, inject_after_exit;
static uint32_t inject_value;
static unsigned enters, exits, published;
static void irq_publish_now(uint32_t value) {
    assert(active && !locked);
    active->frequency_irq_period_cycles = value;
    active->frequency_irq_new_period = true;
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
    assert(result==555 && enters==0 && exits==0);scenarios+=2;
    assert(!labmate_frequency_low_take_period(&app,&result));
    assert(result==555 && !app.frequency_irq_new_period);scenarios++;
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
    assert(result==300 && app.frequency_irq_new_period && app.frequency_irq_period_cycles==400);scenarios++;
    assert(labmate_frequency_low_take_period(&app,&result));
    assert(result==400 && !app.frequency_irq_new_period);scenarios++;
    // Empty mailbox, IRQ on exit: subsequent poll must pick it up.
    inject_after_exit=true;inject_value=500;
    assert(!labmate_frequency_low_take_period(&app,&result));
    assert(result==400 && app.frequency_irq_new_period);scenarios++;
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
        scenarios++;
    }
    assert(!deferred && enters==exits && enters>0 && published>4000);
    printf("Phase2F LOW atomic IRQ mailbox PASS: %u deterministic states\n",scenarios);
    return scenarios==4106?0:1;
}
