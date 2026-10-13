#include "labmate_i2c_scan.h"
#include <string.h>

void labmate_i2c_scan_reset(LabMateI2cScan* scan) {
    memset(scan, 0, sizeof(*scan));
    scan->next_address = LABMATE_I2C_FIRST_ADDR;
    scan->status = LabMateI2cScanIdle;
}

void labmate_i2c_scan_begin(LabMateI2cScan* scan) {
    labmate_i2c_scan_reset(scan);
    scan->status = LabMateI2cScanRunning;
}

bool labmate_i2c_scan_next(LabMateI2cScan* scan, uint8_t* address7) {
    if(!address7 || scan->status != LabMateI2cScanRunning || scan->awaiting_result ||
       scan->next_address > LABMATE_I2C_LAST_ADDR) {
        return false;
    }
    scan->pending_address = scan->next_address;
    scan->awaiting_result = true;
    *address7 = scan->pending_address;
    return true;
}

bool labmate_i2c_scan_record(LabMateI2cScan* scan, uint8_t address7, bool acknowledged) {
    if(scan->status != LabMateI2cScanRunning || !scan->awaiting_result ||
       address7 != scan->pending_address) {
        return false;
    }

    if(acknowledged) {
        if(scan->stored_count < LABMATE_I2C_RESULT_CAP) {
            scan->addresses[scan->stored_count++] = address7;
        }
        scan->total_found++;
    }
    scan->scanned_count++;
    scan->next_address++;
    scan->awaiting_result = false;
    if(scan->next_address > LABMATE_I2C_LAST_ADDR) scan->status = LabMateI2cScanComplete;
    return true;
}

void labmate_i2c_scan_cancel(LabMateI2cScan* scan) {
    if(scan->status == LabMateI2cScanRunning) {
        scan->status = LabMateI2cScanCancelled;
        scan->awaiting_result = false;
    }
}

void labmate_i2c_scan_error(LabMateI2cScan* scan) {
    if(scan->status == LabMateI2cScanRunning) {
        scan->status = LabMateI2cScanError;
        scan->awaiting_result = false;
    }
}

bool labmate_i2c_scan_truncated(const LabMateI2cScan* scan) {
    return scan->total_found > scan->stored_count;
}

bool labmate_i2c_address_encode(uint8_t address7, uint8_t* encoded) {
    if(!encoded || address7 < LABMATE_I2C_FIRST_ADDR ||
       address7 > LABMATE_I2C_LAST_ADDR) {
        return false;
    }
    *encoded = (uint8_t)(address7 << 1U);
    return true;
}
