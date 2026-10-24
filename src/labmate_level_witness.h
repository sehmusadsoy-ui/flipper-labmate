#pragma once
/* Owned GPIO Monitor polling witness, NOT a digital oscilloscope.
 * Clock gap, pin mismatch, ownership loss and interrupted polling invalidate
 * the entire observation. HIGH/LOW describes SAMPLED level, never proof
 * that a physical line was stuck between polls.
 */
#include <stdbool.h>
#include <stdint.h>
#define LABMATE_LEVEL_MAX_GAP_MS 250U
typedef enum {
    LabMateLevelNoEvidence = 0,
    LabMateLevelSampledHigh,
    LabMateLevelSampledLow,
    LabMateLevelTransitions
} LabMateLevelFinding;
typedef struct {
    uint8_t pin;
    uint16_t samples;
    uint16_t transitions;
    uint32_t tick_hz;
    uint32_t start_ms;
    uint32_t last_ms;
    bool level;
    bool active;
    bool sealed;
    bool valid;
} LabMateLevelWitness;
bool labmate_level_begin(
    LabMateLevelWitness* w, uint8_t pin, bool level,
    uint32_t tick, uint32_t tick_hz);
bool labmate_level_observe(
    LabMateLevelWitness* w, uint8_t pin, bool level,
    uint32_t tick, uint32_t tick_hz);
void labmate_level_finish(
    LabMateLevelWitness* w, uint8_t pin, bool released,
    uint32_t tick, uint32_t tick_hz);
void labmate_level_invalidate(LabMateLevelWitness* w);
LabMateLevelFinding labmate_level_assess(
    const LabMateLevelWitness* w, uint32_t required_ms);
