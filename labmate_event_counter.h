#pragma once

#include "labmate_internal.h"

/* Dedicated Event Counter owns PB3 / TIM2_CH2 exclusively while RUN.
 * No GPIO edge ISR; TIM2 external-clock mode counts actual rising edges.
 * The app loop polls and accumulates snapshots; BACK always stops counter.
 */
void labmate_event_counter_start(LabMateApp* app);
void labmate_event_counter_poll(LabMateApp* app);
void labmate_event_counter_stop(LabMateApp* app);
void labmate_event_counter_reset(LabMateApp* app);
