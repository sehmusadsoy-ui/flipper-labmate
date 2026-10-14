#pragma once

#include <stdbool.h>
#include <stdint.h>

/* Pure, HAL-free I2C scan state for an explicitly started, read-only scan.
 * This is NOT an I2C driver and never acquires/configures physical pins.
 */
#define LABMATE_I2C_FIRST_ADDR 0x08U
#define LABMATE_I2C_LAST_ADDR 0x77U
#define LABMATE_I2C_ADDR_COUNT (LABMATE_I2C_LAST_ADDR - LABMATE_I2C_FIRST_ADDR + 1U)
#define LABMATE_I2C_RESULT_CAP 16U

typedef enum {
    LabMateI2cScanIdle = 0,
    LabMateI2cScanRunning,
    LabMateI2cScanComplete,
    LabMateI2cScanCancelled,
    LabMateI2cScanError,
} LabMateI2cScanStatus;

typedef struct {
    LabMateI2cScanStatus status;
    uint8_t next_address;
    uint8_t pending_address;
    uint8_t scanned_count;
    uint8_t total_found;
    uint8_t stored_count;
    uint8_t addresses[LABMATE_I2C_RESULT_CAP];
    bool awaiting_result;
} LabMateI2cScan;

/* Resets statistics/results, but never touches hardware. */
void labmate_i2c_scan_reset(LabMateI2cScan* scan);
void labmate_i2c_scan_begin(LabMateI2cScan* scan);

/* Strict one-address-at-a-time handshake. Calling next twice cannot skip an
 * address. Call record() once with the exact pending address. */
bool labmate_i2c_scan_next(LabMateI2cScan* scan, uint8_t* address7);
bool labmate_i2c_scan_record(LabMateI2cScan* scan, uint8_t address7, bool acknowledged);

/* Cancellation/error preserve the completed partial results but forbid more
 * bus requests; a subsequent begin() resets the session. */
void labmate_i2c_scan_cancel(LabMateI2cScan* scan);
void labmate_i2c_scan_error(LabMateI2cScan* scan);
bool labmate_i2c_scan_truncated(const LabMateI2cScan* scan);

/* Momentum I2C HAL expects address byte (7-bit address shifted left).
 * Validation prevents reserved/out-of-range addresses. */
bool labmate_i2c_address_encode(uint8_t address7, uint8_t* encoded);
