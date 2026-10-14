#include "labmate_ui_screens.h"
#include "labmate_ui_primitives.h"
#include "labmate_i2c_runtime.h"
#include <stdio.h>

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
        message = "OTHER TOOL ACTIVE";
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

    ui_draw_header(canvas, "I2C");
    ui_badge(canvas, 91U, 1U, 35U, badge, scanning);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 3U, 22U, "PC0 SCL / PC1 SDA");
    canvas_draw_line(canvas, 2U, 25U, 125U, 25U);

    if(status == LabMateI2cRuntimeResults) {
        char summary[32];
        snprintf(summary, sizeof(summary), "%u FOUND P%u/%u",
                 (unsigned)result.found_total,
                 (unsigned)(result.page + 1U), (unsigned)result.page_count);
        canvas_draw_str(canvas, 3U, 33U, summary);
        for(uint8_t i = 0; i < result.row_count; ++i) {
            char address[12];
            snprintf(address, sizeof(address), "0x%02X", result.row_address[i]);
            const uint8_t x = (i & 1U) ? 67U : 3U;
            const uint8_t y = (i < 2U) ? 43U : 51U;
            canvas_draw_str(canvas, x, y, address);
        }
    } else {
        canvas_draw_str(canvas, 3U, 38U, message);
        if(status == LabMateI2cRuntimeApiMissing)
            canvas_draw_str(canvas, 3U, 49U, "NO UNSAFE BUS LOCK");
    }
    ui_footer_pair(canvas, "OK", scanning ? "STOP" : "SCAN", "BACK", "EXIT");
}
