#pragma once
#include "labmate_i2c_control.h"
#include <stdbool.h>
#include <stdint.h>

/* Production worker orchestration around a supplied, independently bounded
 * transport. Implementations MUST guarantee acquire_bounded returns within
 * timeout_ms; Momentum's existing furi_hal_i2c_acquire DOES NOT satisfy that
 * contract and must never be plugged in unchanged.
 *
 * This code does not itself perform I2C bus operations. It provides strict
 * STOP/release/scan sequencing so a verified transport can be plugged in.
 */
#define LABMATE_I2C_ACQUIRE_TIMEOUT_MS 50U
#define LABMATE_I2C_PROBE_TIMEOUT_MS 5U

typedef struct {
    void* context;
    bool (*acquire_bounded)(void* context, uint32_t timeout_ms);
    LabMateI2cProbeResult (*probe)(void* context, uint8_t encoded_address, uint32_t timeout_ms);
    void (*release)(void* context);
    /* Thread-safe asynchronous STOP observation is transport-specific. */
    bool (*stop_requested)(void* context);
} LabMateI2cSessionOps;

/* Call from a dedicated worker ONLY, never from GUI/render/input thread.
 * Caller must serialize any concurrent snapshot reads. On every successful
 * acquire exactly one matching release callback is invoked.
 * Returns false on unavailable/invalid transport or hardware error.
 */
bool labmate_i2c_session_execute(
    LabMateI2cControl* control, const LabMateI2cSessionOps* ops);
