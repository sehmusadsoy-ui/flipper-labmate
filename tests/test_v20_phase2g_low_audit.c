/* PC1 one-slot ISR period audit, using the real production C header.
 * These are host interleavings, not proof of native IRQ delivery timing.
 */
#include "labmate_low_mailbox_audit.h"
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <limits.h>

typedef struct {
    LabMateLowMailboxAudit audit;
    uint32_t period;
    bool pending;
} HostMailbox;
static void irq_publish(HostMailbox* m, uint32_t period) {
    labmate_low_mailbox_publish(&m->audit, m->pending);
    m->period = period;
    m->pending = true;
}
static bool consume(HostMailbox* m, uint32_t* period) {
    if(!m->pending) return false;
    *period=m->period;
    m->pending=false;
    return true;
}
int main(void) {
    HostMailbox m={0};
    uint32_t observed=0U, expected_overwrites=0U, prior_period=0U;
    assert(labmate_low_mailbox_detected_loss(NULL));
    labmate_low_mailbox_publish(NULL,true);
    labmate_low_mailbox_reset(NULL);
    assert(!labmate_low_mailbox_detected_loss(&m.audit));
    irq_publish(&m,100U);
    assert(m.audit.publications==1U && m.audit.overwrites==0U);
    assert(consume(&m,&observed) && observed==100U && !m.pending);
    irq_publish(&m,200U);
    irq_publish(&m,300U);
    assert(m.audit.publications==3U && m.audit.overwrites==1U);
    assert(labmate_low_mailbox_detected_loss(&m.audit));
    assert(consume(&m,&observed) && observed==300U);
    labmate_low_mailbox_reset(&m.audit);
    m.pending=false;
    assert(m.audit.publications==0U && !labmate_low_mailbox_detected_loss(&m.audit));

    for(uint32_t i=1;i<=8192U;++i) {
        if((i % 4U)!=0U && m.pending) {
            assert(consume(&m,&prior_period));
        }
        const bool was_pending=m.pending;
        irq_publish(&m,i);
        if(was_pending)++expected_overwrites;
        assert(m.audit.publications==i);
        assert(m.audit.overwrites==expected_overwrites);
        assert(m.period==i && m.pending);
    }
    assert(m.audit.publications==8192U);
    assert(m.audit.overwrites==2048U);
    assert(labmate_low_mailbox_detected_loss(&m.audit));
    assert(consume(&m,&observed) && observed==8192U);
    assert(!consume(&m,&observed));

    /* Wrap must never make a stale publication counter appear fresh. */
    labmate_low_mailbox_reset(&m.audit);
    m.audit.publications=UINT32_MAX-1U;
    labmate_low_mailbox_publish(&m.audit,false);
    assert(m.audit.publications==UINT32_MAX && !m.audit.exhausted);
    labmate_low_mailbox_publish(&m.audit,false);
    assert(m.audit.publications==UINT32_MAX && m.audit.exhausted);
    assert(labmate_low_mailbox_detected_loss(&m.audit));
    labmate_low_mailbox_reset(&m.audit);
    m.audit.overwrites=UINT32_MAX;
    labmate_low_mailbox_publish(&m.audit,true);
    assert(m.audit.overwrites==UINT32_MAX && m.audit.exhausted);
    labmate_low_mailbox_reset(&m.audit);
    assert(!m.audit.exhausted && !labmate_low_mailbox_detected_loss(&m.audit));
    puts("Phase2G PC1 publication audit PASS: 8192 ISR messages, 2048 detected overwrites, saturating counters");
    return 0;
}
