/* Phase 2D: a newer complete sample must have newer physical edge evidence. */
#include "labmate_evidence_session.h"
#include "labmate_dashboard_store.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

static void begin_session(LabMateEvidenceSession* s, uint8_t source) {
    labmate_evidence_session_init(s);
    assert(labmate_evidence_session_begin(s, source, 1U, 100U, 64000000U, true));
}

static bool sample(LabMateEvidenceSession* s, uint32_t count, uint32_t edges) {
    if(s->evidence.source == LabMateSnapshotPulse)
        return labmate_evidence_session_record(s, count, edges, 0U, 0U, 32000U, 32000U, 64000U, 500U);
    return labmate_evidence_session_record(s, count, edges, 0U, 100000U, 0U, 0U, 640000U, 0U);
}

int main(void) {
    unsigned scenarios = 0U;
    const uint8_t sources[] = {LabMateSnapshotFrequency, LabMateSnapshotPulse};
    for(unsigned k = 0U; k < 2U; ++k) {
        LabMateEvidenceSession s;
        LabMateSnapshotV1 out;
        begin_session(&s, sources[k]);
        assert(sample(&s, 1U, 2U));
        assert(!sample(&s, 2U, 2U)); /* A new sample CANNOT reuse previous edges. */
        assert(s.sample_fault);
        assert(!sample(&s, 3U, 5U)); /* Sticky poisoning. */
        assert(labmate_evidence_session_finish(&s, 200U, true, &out));
        assert(out.quality == LabMateSnapshotInvalid);
        ++scenarios;

        begin_session(&s, sources[k]);
        assert(!sample(&s, 1U, 0U)); /* Complete sample with zero edges is false. */
        assert(labmate_evidence_session_finish(&s, 200U, true, &out));
        assert(out.quality == LabMateSnapshotInvalid);
        ++scenarios;

        begin_session(&s, sources[k]);
        assert(sample(&s, 1U, 2U));
        assert(sample(&s, 2U, 4U));
        assert(labmate_evidence_session_finish(&s, 200U, true, &out));
        assert(out.quality == LabMateSnapshotValid);
        ++scenarios;

        begin_session(&s, sources[k]);
        assert(sample(&s, 1U, UINT32_MAX));
        assert(!sample(&s, 2U, 0U)); /* Edge counter wrap is an epoch error. */
        assert(labmate_evidence_session_finish(&s, 200U, true, &out));
        assert(out.quality == LabMateSnapshotInvalid);
        ++scenarios;
    }
    printf("Phase2D fresh-edge evidence PASS: %u scenarios\n", scenarios);
    return scenarios == 8U ? 0 : 1;
}
