#pragma once
/* Device app-thread adapter for real Frequency Meter native publications.
 * The HAL source still owns every IRQ/lease, and this NEVER changes capture.
 * VALID is permitted only after verified E11 STOP/teardown.
 */
#include "labmate_internal.h"

void labmate_doctor_frequency_started(LabMateApp* app);
void labmate_doctor_frequency_note_low(
    LabMateApp* app, const LabMateLowMailboxObservation* observation,
    uint32_t coherent_edges, uint32_t coherent_last_edge_tick);
void labmate_doctor_frequency_note_high(LabMateApp* app);
void labmate_doctor_frequency_prepare_stop(LabMateApp* app);
void labmate_doctor_frequency_finish_stop(LabMateApp* app);
void labmate_doctor_frequency_abandon(LabMateApp* app);
