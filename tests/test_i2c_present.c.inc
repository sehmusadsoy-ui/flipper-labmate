/* Passive I2C snapshot tests. This does NOT operate a real I2C bus. */
#include "labmate_i2c_present.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void test_unscanned_and_blocked(void) {
    LabMateI2cControl c;
    LabMateI2cView v;
    uint32_t generation;
    uint8_t addr;
    labmate_i2c_control_reset(&c);
    assert(!labmate_i2c_present(NULL, 0U, &v));
    assert(!labmate_i2c_present(&c, 0U, NULL));
    assert(labmate_i2c_present(&c, 255U, &v));
    assert(v.status == LabMateI2cViewNotScanned);
    assert(v.page_count == 1U && v.page == 0U && v.row_count == 0U);
    assert(v.model_quiescent && !v.truncated);
    assert(v.found_total == 0U && v.scanned_count == 0U);
    assert(strcmp(labmate_i2c_view_status_text(v.status), "NOT SCANNED") == 0);

    assert(labmate_i2c_control_start(&c, &generation));
    assert(labmate_i2c_present(&c, 0U, &v));
    assert(v.status == LabMateI2cViewWaitBus);
    assert(!v.model_quiescent && v.found_total == 0U);
    assert(labmate_i2c_control_request_stop(&c));
    assert(labmate_i2c_present(&c, 0U, &v));
    assert(v.status == LabMateI2cViewStopPending);
    assert(!v.model_quiescent && !v.row_count);
    assert(!labmate_i2c_control_next_probe(&c, &addr));
    assert(labmate_i2c_control_acquire_done(&c, generation, true));
    assert(labmate_i2c_present(&c, 0U, &v));
    assert(v.status == LabMateI2cViewReleasing && !v.model_quiescent);
    assert(labmate_i2c_control_release_done(&c, generation));
    assert(labmate_i2c_present(&c, 0U, &v));
    assert(v.status == LabMateI2cViewCancelled && v.model_quiescent);
}

/* Distinguish firmware external-mutex contention from scan errors. */
static void test_bounded_acquire_busy_snapshot(void) {
    LabMateI2cControl c;
    LabMateI2cView v;
    uint32_t generation;
    labmate_i2c_control_reset(&c);
    assert(labmate_i2c_control_start(&c, &generation));
    assert(labmate_i2c_control_acquire_done(&c, generation, false));
    assert(c.state == LabMateI2cControlBusy && !c.bus_held);
    assert(labmate_i2c_present(&c, 0U, &v));
    assert(v.status == LabMateI2cViewBusy && v.model_quiescent);
    assert(v.found_total == 0U && v.scanned_count == 0U && v.row_count == 0U);
    assert(strcmp(labmate_i2c_view_status_text(v.status), "BUSY") == 0);
    assert(labmate_i2c_control_start(&c, &generation));
    assert(labmate_i2c_present(&c, 0U, &v));
    assert(v.status == LabMateI2cViewWaitBus);
}

static void test_no_device_only_after_real_model_finish(void) {
    LabMateI2cControl c;
    LabMateI2cView v;
    uint32_t generation;
    uint8_t a;
    labmate_i2c_control_reset(&c);
    assert(labmate_i2c_control_start(&c, &generation));
    assert(labmate_i2c_control_acquire_done(&c, generation, true));
    assert(labmate_i2c_present(&c, 0U, &v));
    assert(v.status == LabMateI2cViewScanning);
    for(unsigned i = LABMATE_I2C_FIRST_ADDR; i <= LABMATE_I2C_LAST_ADDR; ++i) {
        assert(labmate_i2c_control_next_probe(&c, &a));
        assert(a == i);
        assert(labmate_i2c_control_probe_done(&c, generation, a, LabMateI2cProbeNoAck));
    }
    assert(labmate_i2c_present(&c, 0U, &v));
    assert(v.status == LabMateI2cViewReleasing && !v.model_quiescent);
    assert(labmate_i2c_control_release_done(&c, generation));
    assert(labmate_i2c_present(&c, 0U, &v));
    assert(v.status == LabMateI2cViewNoDevices);
    assert(v.scanned_count == LABMATE_I2C_ADDR_COUNT && v.found_total == 0U);
    assert(v.page_count == 1U && v.row_count == 0U && v.model_quiescent);
    assert(strcmp(labmate_i2c_view_status_text(v.status), "NO DEVICES") == 0);
}

static void test_pages_results_and_truncation(void) {
    LabMateI2cControl c;
    LabMateI2cView v;
    uint32_t generation;
    uint8_t a;
    labmate_i2c_control_reset(&c);
    assert(labmate_i2c_control_start(&c, &generation));
    assert(labmate_i2c_control_acquire_done(&c, generation, true));
    for(unsigned i = LABMATE_I2C_FIRST_ADDR; i <= LABMATE_I2C_LAST_ADDR; ++i) {
        assert(labmate_i2c_control_next_probe(&c, &a));
        assert(labmate_i2c_control_probe_done(&c, generation, a, LabMateI2cProbeAck));
    }
    assert(labmate_i2c_control_release_done(&c, generation));
    assert(labmate_i2c_present(&c, 0U, &v));
    assert(v.status == LabMateI2cViewResults && v.model_quiescent);
    assert(v.scanned_count == LABMATE_I2C_ADDR_COUNT);
    assert(v.found_total == LABMATE_I2C_ADDR_COUNT);
    assert(v.stored_count == LABMATE_I2C_RESULT_CAP && v.truncated);
    assert(v.page_count == 4U && v.page == 0U);
    assert(v.row_count == 4U && v.row_address[0] == 0x08U);
    assert(v.row_address[3] == 0x0BU);
    assert(labmate_i2c_present(&c, 1U, &v));
    assert(v.page_count == 4U && v.page == 1U);
    assert(v.row_address[0] == 0x0CU && v.row_address[3] == 0x0FU);
    assert(labmate_i2c_present(&c, 255U, &v));
    assert(v.requested_page == 255U && v.page == 3U);
    assert(v.row_count == 4U && v.row_address[0] == 0x14U);
    assert(v.row_address[3] == 0x17U);

    /* Defensive handling: never index beyond storage, even if count corrupts. */
    c.scan.stored_count = 255U;
    assert(labmate_i2c_present(&c, 255U, &v));
    assert(v.stored_count == LABMATE_I2C_RESULT_CAP);
    assert(v.page == 3U && v.row_count == 4U);
}

static void test_partial_cancel_and_error(void) {
    LabMateI2cControl c;
    LabMateI2cView v;
    uint32_t generation;
    uint8_t a;
    labmate_i2c_control_reset(&c);
    assert(labmate_i2c_control_start(&c, &generation));
    assert(labmate_i2c_control_acquire_done(&c, generation, true));
    assert(labmate_i2c_control_next_probe(&c, &a) && a == 0x08U);
    assert(labmate_i2c_control_probe_done(&c, generation, a, LabMateI2cProbeAck));
    assert(labmate_i2c_control_next_probe(&c, &a));
    assert(labmate_i2c_control_request_stop(&c));
    assert(labmate_i2c_present(&c, 0U, &v));
    assert(v.status == LabMateI2cViewStopPending);
    assert(!v.model_quiescent && v.row_count == 1U);
    assert(labmate_i2c_control_probe_done(&c, generation, a, LabMateI2cProbeNoAck));
    assert(labmate_i2c_present(&c, 0U, &v));
    assert(v.status == LabMateI2cViewReleasing);
    assert(labmate_i2c_control_release_done(&c, generation));
    assert(labmate_i2c_present(&c, 0U, &v));
    assert(v.status == LabMateI2cViewCancelled && v.model_quiescent);
    assert(v.row_count == 1U && v.row_address[0] == 0x08U);
    assert(v.scanned_count == 2U && v.found_total == 1U);
    assert(labmate_i2c_control_start(&c, &generation));
    assert(labmate_i2c_control_acquire_done(&c, generation, true));
    assert(labmate_i2c_control_next_probe(&c, &a));
    assert(labmate_i2c_control_probe_done(&c, generation, a, LabMateI2cProbeError));
    assert(labmate_i2c_control_release_done(&c, generation));
    assert(labmate_i2c_present(&c, 0U, &v));
    assert(v.status == LabMateI2cViewFailed && v.model_quiescent);
    assert(v.found_total == 0U && v.row_count == 0U);
    assert(strcmp(labmate_i2c_view_status_text(v.status), "ERROR") == 0);
    assert(strcmp(labmate_i2c_view_status_text((LabMateI2cViewStatus)99), "ERROR") == 0);
}

int main(void) {
    test_unscanned_and_blocked();
    test_bounded_acquire_busy_snapshot();
    test_no_device_only_after_real_model_finish();
    test_pages_results_and_truncation();
    test_partial_cancel_and_error();
    puts("I2C UI presentation: honest statuses, four-row paging, clamp, truncation, STOP pending and error PASS (HOST ONLY)");
    return 0;
}
