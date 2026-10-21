#pragma once
/* Phase 2E: app-thread-only accounting for actual producer publication events.
 * No HAL, ISR, lease, wall-clock, resource teardown or storage operations.
 * A caller MUST obtain candidate fields from the actual native producer.
 * Passing the publication flag does NOT independently prove an IRQ occurred.
 */
#include <stdbool.h>
#include <stdint.h>

typedef enum {
    LabMatePublicationFrequencyLow = 0,
    LabMatePublicationFrequencyHigh,
    LabMatePublicationPulse,
} LabMatePublicationPath;

typedef enum {
    LabMatePublicationWait = 0,
    LabMatePublicationAccepted,
    LabMatePublicationFault,
} LabMatePublicationResult;

typedef struct {
    /* A low ISR period was consumed / high TIM2 gate returned Publish /
     * Pulse widths were copied coherently with both validity flags set.
     * No UI display-only status is sufficient for this flag. */
    bool native_publication_confirmed;
    bool native_clock_safe;
    uint32_t observed_at_ms; /* same monotonic, unwrapped epoch as begin */
    uint32_t cumulative_edges; /* real IRQ edges or TIM2 hardware count */
    uint32_t frequency_millihz; /* native producer's published frequency */
    uint32_t high_ticks;
    uint32_t low_ticks;
    uint32_t period_ticks;
    uint16_t duty_permille;
} LabMatePublicationCandidate;

typedef struct {
    bool active;
    bool poisoned;
    LabMatePublicationPath path;
    uint8_t pin_index;
    uint32_t start_ms;
    uint32_t previous_ms;
    uint32_t previous_edges;
    uint32_t accepted_publications; /* NOT raw completed period count */
} LabMatePublicationGate;

/* Initialize only at application epoch creation. Not a valid way to clear a
 * native release fault; requires separate confirmed resource teardown. */
void labmate_publication_gate_init(LabMatePublicationGate* gate);

/* Call only after actual native resource acquisition. Refuses unsupported
 * source pins, repeated begin, and missing ownership proof. */
bool labmate_publication_gate_begin(
    LabMatePublicationGate* gate, LabMatePublicationPath path, uint8_t pin_index,
    uint32_t start_ms, bool ownership_confirmed);

/* Returns WAIT for no publication; ACCEPTED only for a new, consistent
 * native publication, NEVER for an in-progress sample. Bad publication
 * permanently poisons the gate until an independent teardown/new epoch.
 * Accepted publication count must not be used as a raw IRQ period counter. */
LabMatePublicationResult labmate_publication_gate_observe(
    LabMatePublicationGate* gate, const LabMatePublicationCandidate* candidate);
