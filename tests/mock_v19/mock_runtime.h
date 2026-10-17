#pragma once
#include "furi_hal.h"
#include <stdbool.h>
#include <stdint.h>
typedef struct {
    void (*callback)(void*);
    void* callback_context;
    bool callback_enabled;
    bool foreign_callback;
    bool lease_occupied;
    bool refuse_release;
    bool input_level;
    uint32_t held_handle;
    uint32_t gpio_writes;
    uint32_t exti_writes;
    uint32_t callback_removes;
    uint32_t lease_releases;
    uint32_t critical_depth;
} LabMateMockHal;
extern LabMateMockHal labmate_mock_hal;
void labmate_mock_reset(void);
void labmate_mock_edge(uint32_t tick, bool high);
