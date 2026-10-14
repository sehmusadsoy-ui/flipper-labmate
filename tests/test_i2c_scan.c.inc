/* Native deterministic tests: NO Flipper HAL and NO physical GPIO. */
#include "labmate_i2c_scan.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void check_addresses(void) {
    uint8_t encoded = 0xAAU;
    assert(!labmate_i2c_address_encode(0x00U, &encoded));
    assert(!labmate_i2c_address_encode(0x07U, &encoded));
    assert(!labmate_i2c_address_encode(0x78U, &encoded));
    assert(!labmate_i2c_address_encode(0xFFU, &encoded));
    assert(!labmate_i2c_address_encode(0x20U, NULL));
    assert(encoded == 0xAAU);
    assert(labmate_i2c_address_encode(0x08U, &encoded) && encoded == 0x10U);
    assert(labmate_i2c_address_encode(0x3CU, &encoded) && encoded == 0x78U);
    assert(labmate_i2c_address_encode(0x77U, &encoded) && encoded == 0xEEU);
}

static void check_all_empty_and_duplicate(void) {
    LabMateI2cScan s;
    labmate_i2c_scan_reset(&s);
    assert(s.status == LabMateI2cScanIdle && !s.scanned_count && !s.total_found);
    uint8_t got = 0U;
    assert(!labmate_i2c_scan_next(&s, &got));
    labmate_i2c_scan_begin(&s);
    assert(!labmate_i2c_scan_next(&s, NULL));
    for(unsigned i = LABMATE_I2C_FIRST_ADDR; i <= LABMATE_I2C_LAST_ADDR; ++i) {
        assert(labmate_i2c_scan_next(&s, &got));
        assert(got == i);
        assert(!labmate_i2c_scan_next(&s, &got));
        assert(!labmate_i2c_scan_record(&s, (uint8_t)(i == LABMATE_I2C_LAST_ADDR ? i-1U : i+1U), false));
        assert(labmate_i2c_scan_record(&s, got, false));
        assert(!labmate_i2c_scan_record(&s, got, true));
    }
    assert(s.status == LabMateI2cScanComplete);
    assert(s.scanned_count == LABMATE_I2C_ADDR_COUNT);
    assert(s.total_found == 0U && s.stored_count == 0U);
    assert(!labmate_i2c_scan_truncated(&s));
    assert(!labmate_i2c_scan_next(&s, &got));
    assert(!labmate_i2c_scan_record(&s, 0x77U, true));
}

static void check_sparse_and_bounded(void) {
    LabMateI2cScan s;
    uint8_t a;
    labmate_i2c_scan_begin(&s);
    while(labmate_i2c_scan_next(&s, &a)) {
        bool present = a == 0x20U || a == 0x3CU || a == 0x68U;
        assert(labmate_i2c_scan_record(&s, a, present));
    }
    assert(s.status == LabMateI2cScanComplete);
    assert(s.stored_count == 3U && s.total_found == 3U);
    assert(s.addresses[0] == 0x20U && s.addresses[1] == 0x3CU && s.addresses[2] == 0x68U);
    labmate_i2c_scan_begin(&s);
    while(labmate_i2c_scan_next(&s, &a)) {
        assert(labmate_i2c_scan_record(&s, a, true));
    }
    assert(s.status == LabMateI2cScanComplete);
    assert(s.total_found == LABMATE_I2C_ADDR_COUNT);
    assert(s.stored_count == LABMATE_I2C_RESULT_CAP);
    assert(labmate_i2c_scan_truncated(&s));
    assert(s.addresses[0] == LABMATE_I2C_FIRST_ADDR);
    assert(s.addresses[LABMATE_I2C_RESULT_CAP-1U] == LABMATE_I2C_FIRST_ADDR+LABMATE_I2C_RESULT_CAP-1U);
}

static void check_cancel_and_error(void) {
    LabMateI2cScan s;
    uint8_t a;
    labmate_i2c_scan_begin(&s);
    assert(labmate_i2c_scan_next(&s, &a) && a == 0x08U);
    assert(labmate_i2c_scan_record(&s, a, true));
    assert(labmate_i2c_scan_next(&s, &a) && a == 0x09U);
    labmate_i2c_scan_cancel(&s);
    assert(s.status == LabMateI2cScanCancelled);
    assert(!s.awaiting_result && s.scanned_count == 1U && s.total_found == 1U);
    assert(!labmate_i2c_scan_record(&s, 0x09U, true));
    assert(!labmate_i2c_scan_next(&s, &a));
    labmate_i2c_scan_cancel(&s);
    labmate_i2c_scan_begin(&s);
    assert(s.total_found == 0U && s.scanned_count == 0U);
    assert(labmate_i2c_scan_next(&s, &a));
    labmate_i2c_scan_error(&s);
    assert(s.status == LabMateI2cScanError);
    assert(!s.awaiting_result && !labmate_i2c_scan_next(&s, &a));
    labmate_i2c_scan_begin(&s);
    assert(s.status == LabMateI2cScanRunning && s.next_address == 0x08U);
}

int main(void) {
    check_addresses();
    check_all_empty_and_duplicate();
    check_sparse_and_bounded();
    check_cancel_and_error();
    puts("I2C pure scanner: bounds, shift, 112 addresses, duplicate rejection, cancellation, overflow and recovery PASS");
    return 0;
}
