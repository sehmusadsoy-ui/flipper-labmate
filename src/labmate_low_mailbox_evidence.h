#pragma once
/* Phase 2H: fail-closed LOW/PC1 mailbox provenance -> snapshot quality.
 * Does not fabricate complete samples, IRQ edges, timing or lease release.
 */
#include "labmate_low_mailbox_audit.h"
#include "labmate_snapshot_bridge.h"

static inline bool labmate_low_mailbox_apply_evidence(
    const LabMateLowMailboxObservation* observed,
    LabMateCaptureEvidenceV1* evidence) {
    if(!observed || !evidence || evidence->source != LabMateSnapshotFrequency ||
       evidence->pin_index != 1U) return false;
    /* A coalesced publication is NOT a raw missed edge count. */
    if(observed->overwrites != 0U || observed->exhausted) evidence->overflow = true;
    /* Without a fresh pending period, do not present an old UI result. */
    if(!observed->has_period || observed->publications == 0U)
        evidence->measurement_valid = false;
    return true;
}
