#include "labmate_ui_screens.h"
#include "labmate_comm_ui.h"
#include "labmate_i2c_runtime.h"
#include <stdio.h>

/* Present a snapshot only; no bus acquisition or scan from drawing code. */
void draw_i2c(Canvas* canvas, LabMateApp* app) {
    LabMateI2cView result;
    const LabMateI2cRuntimeStatus status =
        labmate_i2c_runtime_snapshot(app->i2c, app->i2c_page, &result);
    const char* badge = "READY";
    const char* message = "OK: SCAN 3.3V";
    const bool scanning = status == LabMateI2cRuntimeScanning;

    switch(status) {
    case LabMateI2cRuntimeApiMissing:
        badge = "FW API";
        message = "NEEDS TIMED FW API";
        break;
    case LabMateI2cRuntimeBusy:
        badge = "BUSY";
        message = "I2C BUS / TOOL BUSY";
        break;
    case LabMateI2cRuntimeScanning:
        badge = "RUN";
        message = "SCANNING BUS...";
        break;
    case LabMateI2cRuntimeResults:
        badge = "DONE";
        message = "REAL ACK RESULTS";
        break;
    case LabMateI2cRuntimeNoDevices:
        badge = "NONE";
        /* HAL reports NACK and transfer timeout alike as false. */
        message = "NO ACKS / CHECK BUS";
        break;
    case LabMateI2cRuntimeCancelled:
        badge = "STOP";
        message = "SCAN CANCELLED";
        break;
    case LabMateI2cRuntimeFailed:
        badge = "ERR";
        message = "BUS / SCAN ERROR";
        break;
    default:
        break;
    }

    labmate_comm_ui_header(canvas, "I2C", badge, scanning);
    canvas_set_font(canvas, FontSecondary);
    canvas_set_color(canvas, ColorBlack);
    (void)ui_kit_text(canvas, 4U, 20U, 120U, "PC0 SCL / PC1 SDA", NULL);
    canvas_draw_line(canvas, 4U, 24U, 123U, 24U);

    if(status == LabMateI2cRuntimeResults) {
        char summary[32];
        snprintf(summary, sizeof(summary), "%u FOUND P%u/%u",
                 (unsigned)result.found_total,
                 (unsigned)(result.page + 1U), (unsigned)result.page_count);
        (void)ui_kit_text(canvas, 4U, 33U, 120U, summary, NULL);
        for(uint8_t i = 0U; i < result.row_count && i < 4U; ++i) {
            char address[12];
            snprintf(address, sizeof(address), "0x%02X", result.row_address[i]);
            const uint8_t x = (i & 1U) ? 67U : 4U;
            const uint8_t y = (i < 2U) ? 43U : 51U;
            (void)ui_kit_text(canvas, x, y, 60U, address, NULL);
        }
    } else {
        (void)ui_kit_text(canvas, 4U, 38U, 120U, message, NULL);
        if(status == LabMateI2cRuntimeApiMissing)
            (void)ui_kit_text(canvas, 4U, 49U, 120U, "NO UNSAFE BUS LOCK", NULL);
    }
    labmate_comm_ui_keys(canvas, UiKitKeyOk, scanning ? "Stop" : "Scan",
                         UiKitKeyBack, "Exit");
}
