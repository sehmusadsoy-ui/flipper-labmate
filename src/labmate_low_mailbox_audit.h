#pragma once
/* Phase 2G: IRQ-owned LOW/PC1 one-slot publication audit.
 * Counts completed ISR *publications*, not rising edges or LCD samples.
 * No SDK, GPIO, heap, clock or resource access in this header.
 * Reader must take a coherent snapshot with IRQs excluded.
 */
#include <stdbool.h>
#include <stdint.h>
#include <limits.h>

typedef struct {
    volatile uint32_t publications;
    volatile uint32_t overwrites;
    volatile bool exhausted;
} LabMateLowMailboxAudit;

/* Reset ONLY while the native callback is disabled, following successful
 * ownership acquisition. Never reset on HOLD, display refresh or logger tick.
 */
static inline void labmate_low_mailbox_reset(LabMateLowMailboxAudit* audit) {
    if(!audit) return;
    audit->publications = 0U;
    audit->overwrites = 0U;
    audit->exhausted = false;
}

/* Call once immediately before replacing the ISR's period/flag pair.
 * pending_before means a previous ISR value is still unconsumed.
 * Saturate instead of allowing a wrapped generation to appear fresh.
 * An exhausted counter is a permanent no-provenance condition this session.
 */
static inline void labmate_low_mailbox_publish(
    LabMateLowMailboxAudit* audit, bool pending_before) {
    if(!audit) return;
    if(audit->publications == UINT32_MAX) {
        audit->exhausted = true;
    } else {
        ++audit->publications;
    }
    if(pending_before) {
        if(audit->overwrites == UINT32_MAX) {
            audit->exhausted = true;
        } else {
            ++audit->overwrites;
        }
    }
}

/* Advisory only: FALSE does not prove lossless hardware acquisition.
 * Unread flag / IRQ delivery / native lease must be independently verified.
 */
static inline bool labmate_low_mailbox_detected_loss(
    const LabMateLowMailboxAudit* audit) {
    return !audit || audit->overwrites != 0U || audit->exhausted;
}
