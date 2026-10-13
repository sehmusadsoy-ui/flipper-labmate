/* Isolated safe I2C UX DEMO. Nothing here communicates with I2C hardware.
 * Every screen displays a permanent SIMULATED / NO BUS notice.
 * This is intentionally NOT compiled into production labmate.fap.
 */
#include <furi.h>
#include <gui/gui.h>
#include <gui/view_port.h>
#include <gui/canvas.h>
#include <input/input.h>
#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>

#include "../../src/labmate_i2c_scan.c"
#include "../../src/labmate_i2c_control.c"
#include "../../src/labmate_i2c_present.c"

#define PREVIEW_SCENES 9U

typedef struct {
    LabMateI2cControl control;
    LabMateI2cView snapshot;
    uint8_t scene;
    uint8_t page;
    FuriMutex* lock; /* Guards snapshot/scene across GUI and input threads. */
} LabMateI2cDemo;

static void demo_build(LabMateI2cDemo* demo) {
    LabMateI2cControl* c = &demo->control;
    uint32_t token = 0U;
    uint8_t addr = 0U;

    labmate_i2c_control_reset(c);
    if(demo->scene != 0U) {
        labmate_i2c_control_start(c, &token);

        if(demo->scene == 2U) {
            labmate_i2c_control_request_stop(c);
        } else if(demo->scene >= 3U) {
            /* SIMULATED acquire completion: no HAL call or real owner exists. */
            labmate_i2c_control_acquire_done(c, token, true);
            if(demo->scene == 3U || demo->scene == 4U || demo->scene == 5U) {
                while(labmate_i2c_control_next_probe(c, &addr)) {
                    bool ack = demo->scene == 5U ||
                               (demo->scene == 4U &&
                                (addr == 0x20U || addr == 0x21U ||
                                 addr == 0x3CU || addr == 0x40U ||
                                 addr == 0x48U || addr == 0x68U ||
                                 addr == 0x76U));
                    labmate_i2c_control_probe_done(
                        c, token, addr, ack ? LabMateI2cProbeAck : LabMateI2cProbeNoAck);
                }
                labmate_i2c_control_release_done(c, token);
            } else if(demo->scene == 6U) {
                labmate_i2c_control_next_probe(c, &addr);
                labmate_i2c_control_probe_done(c, token, addr, LabMateI2cProbeAck);
                labmate_i2c_control_request_stop(c);
                labmate_i2c_control_release_done(c, token);
            } else if(demo->scene == 7U) {
                labmate_i2c_control_next_probe(c, &addr);
                labmate_i2c_control_probe_done(c, token, addr, LabMateI2cProbeError);
                labmate_i2c_control_release_done(c, token);
            } else if(demo->scene == 8U) {
                labmate_i2c_control_request_stop(c);
                /* Deliberately no release_done(): demonstrate RELEASING. */
            }
        }
    }
    demo->page = 0U;
    labmate_i2c_present(c, 0U, &demo->snapshot);
}

static void demo_draw(Canvas* canvas, void* context) {
    const LabMateI2cDemo* demo = context;
    /* Snapshot under short GUI-state lock; never draw with it held. */
    furi_mutex_acquire(demo->lock, FuriWaitForever);
    const LabMateI2cView copy = demo->snapshot;
    const uint8_t scene = demo->scene;
    furi_mutex_release(demo->lock);
    const LabMateI2cView* v = &copy;
    char text[35];

    canvas_clear(canvas);
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 2, 10, "I2C UX DEMO");
    canvas_set_font(canvas, FontSecondary);

    snprintf(text, sizeof(text), "%u/%u", (unsigned)(scene + 1U),
             (unsigned)PREVIEW_SCENES);
    canvas_draw_str(canvas, 101, 10, text);
    canvas_draw_line(canvas, 0, 12, 127, 12);

    canvas_draw_str(canvas, 3, 21, "SIMULATED - NO BUS");
    snprintf(text, sizeof(text), "STATUS: %s",
             labmate_i2c_view_status_text(v->status));
    canvas_draw_str(canvas, 3, 30, text);

    snprintf(text, sizeof(text), "S:%03u F:%03u P:%u/%u%s",
             (unsigned)v->scanned_count, (unsigned)v->found_total,
             (unsigned)(v->page + 1U), (unsigned)v->page_count,
             v->truncated ? "+" : "");
    canvas_draw_str(canvas, 3, 39, text);

    for(uint8_t i = 0U; i < v->row_count; ++i) {
        snprintf(text, sizeof(text), "0x%02X", (unsigned)v->row_address[i]);
        canvas_draw_str(canvas, (i & 1U) ? 68 : 6, (i / 2U) ? 55 : 47, text);
    }
    canvas_draw_line(canvas, 0, 57, 127, 57);
    canvas_draw_str(canvas, 3, 63, "LR SCENE  UD PAGE  BK");
}

static void demo_input(InputEvent* event, void* context) {
    FuriMessageQueue* queue = context;
    /* Drop on full queue; no time-blocking in input callback. */
    furi_message_queue_put(queue, event, 0U);
}

int32_t labmate_i2c_ui_preview_app(void* args) {
    UNUSED(args);
    LabMateI2cDemo demo = {.scene = 0U, .page = 0U};
    demo.lock = furi_mutex_alloc(FuriMutexTypeNormal);
    demo_build(&demo);

    FuriMessageQueue* queue = furi_message_queue_alloc(8U, sizeof(InputEvent));
    ViewPort* viewport = view_port_alloc();
    view_port_draw_callback_set(viewport, demo_draw, &demo);
    view_port_input_callback_set(viewport, demo_input, queue);
    Gui* gui = furi_record_open(RECORD_GUI);
    gui_add_view_port(gui, viewport, GuiLayerFullscreen);

    bool running = true;
    while(running) {
        InputEvent event;
        if(furi_message_queue_get(queue, &event, FuriWaitForever) != FuriStatusOk) continue;
        if(event.type != InputTypeShort && event.type != InputTypeRepeat) continue;
        if(event.key == InputKeyBack) {
            running = false;
        } else if(event.key == InputKeyLeft || event.key == InputKeyRight) {
            furi_mutex_acquire(demo.lock, FuriWaitForever);
            if(event.key == InputKeyLeft) {
                demo.scene = demo.scene ? (uint8_t)(demo.scene - 1U) : PREVIEW_SCENES - 1U;
            } else {
                demo.scene = (uint8_t)((demo.scene + 1U) % PREVIEW_SCENES);
            }
            demo_build(&demo);
            furi_mutex_release(demo.lock);
            view_port_update(viewport);
        } else if(event.key == InputKeyUp || event.key == InputKeyDown) {
            furi_mutex_acquire(demo.lock, FuriWaitForever);
            uint8_t count = demo.snapshot.page_count;
            if(count == 0U) count = 1U;
            if(event.key == InputKeyDown) {
                demo.page = (uint8_t)((demo.page + 1U) % count);
            } else {
                demo.page = demo.page ? (uint8_t)(demo.page - 1U) : (uint8_t)(count - 1U);
            }
            labmate_i2c_present(&demo.control, demo.page, &demo.snapshot);
            furi_mutex_release(demo.lock);
            view_port_update(viewport);
        }
    }

    view_port_enabled_set(viewport, false);
    gui_remove_view_port(gui, viewport);
    furi_record_close(RECORD_GUI);
    view_port_free(viewport);
    furi_message_queue_free(queue);
    furi_mutex_free(demo.lock);
    return 0;
}
