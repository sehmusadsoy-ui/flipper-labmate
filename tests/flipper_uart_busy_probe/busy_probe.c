/* LabMate v1.8 stand-alone physical UART owner diagnostic.
 *
 * THIS IS NOT A REPLACEMENT FOR labmate.fap.
 * With Flipper Wi-Fi Devboard and other GPIO peripherals DETACHED,
 * reserve the real USART control handle; call LabMate's real UART
 * startup routine, demand BUSY without seizing the reserved handle;
 * release the handle and verify ordinary LabMate start/stop still works.
 * Sends no UART TX bytes; does not modify persistent firmware/storage.
 *
 * The LabMate implementation is included directly from the parent
 * repository to test the actual production code without copying it.
 */
#include <furi.h>
#include <gui/gui.h>
#include <gui/view_port.h>
#include <gui/canvas.h>
#include <input/input.h>
#include <expansion/expansion.h>
#include <furi_hal_serial_control.h>
#include <stdbool.h>

/* Include real source, not test doubles. Only this FAP compiles them. */
#include "../../src/labmate_uart_text.c"
#include "../../src/labmate_uart.c"

typedef enum {
    ProbeReady,
    ProbePass,
    ProbeFailBusy,
    ProbeFailRecovery,
    ProbeSkipExpansion,
    ProbeSkipOwned,
} ProbeState;

typedef struct {
    ProbeState state;
} ProbeContext;

static void probe_render(Canvas* canvas, void* context) {
    const ProbeContext* probe = context;
    canvas_clear(canvas);
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 3, 12, "UART BUSY PROBE");
    canvas_set_font(canvas, FontSecondary);
    switch(probe->state) {
    case ProbeReady:
        canvas_draw_str(canvas, 3, 25, "Board disconnected?");
        canvas_draw_str(canvas, 3, 36, "OK: test  BACK: exit");
        break;
    case ProbePass:
        canvas_draw_str(canvas, 3, 25, "BUSY REFUSAL: PASS");
        canvas_draw_str(canvas, 3, 36, "RESTART/STOP: PASS");
        break;
    case ProbeFailBusy:
        canvas_draw_str(canvas, 3, 25, "FAIL: BUSY not safe");
        canvas_draw_str(canvas, 3, 36, "Port released");
        break;
    case ProbeFailRecovery:
        canvas_draw_str(canvas, 3, 25, "BUSY refusal: PASS");
        canvas_draw_str(canvas, 3, 36, "FAIL: restart");
        break;
    case ProbeSkipExpansion:
        canvas_draw_str(canvas, 3, 25, "SKIP: expansion busy");
        canvas_draw_str(canvas, 3, 36, "No resources taken");
        break;
    case ProbeSkipOwned:
        canvas_draw_str(canvas, 3, 25, "SKIP: UART owned");
        canvas_draw_str(canvas, 3, 36, "No resources taken");
        break;
    }
    canvas_draw_str(canvas, 3, 57, "BACK exit / OK repeat");
}

static void probe_input(InputEvent* event, void* context) {
    FuriMessageQueue* queue = context;
    furi_message_queue_put(queue, event, 0);
}

static ProbeState probe_execute(void) {
    /* Do not interfere with a connected expansion module or its owner. */
    Expansion* expansion = furi_record_open(RECORD_EXPANSION);
    const bool connected = expansion_is_connected(expansion);
    furi_record_close(RECORD_EXPANSION);
    if(connected) return ProbeSkipExpansion;

    /* Reserve the REAL hardware USART, not a simulated HAL object. */
    FuriHalSerialHandle* reserved = furi_hal_serial_control_acquire(FuriHalSerialIdUsart);
    if(!reserved) return ProbeSkipOwned;

    LabMateUart uart;
    labmate_uart_reset(&uart);
    const bool unexpected_start = labmate_uart_start(&uart);
    const bool busy_pass =
        !unexpected_start && uart.blocked && !uart.active && uart.serial == NULL &&
        uart.stream == NULL && uart.expansion == NULL;
    labmate_uart_stop(&uart);

    /* Release the test owner's handle before attempting restoration. */
    furi_hal_serial_control_release(reserved);
    if(!busy_pass) return ProbeFailBusy;

    const bool restart_ok = labmate_uart_start(&uart);
    const bool recovered = restart_ok && uart.active && !uart.blocked && uart.serial != NULL;
    labmate_uart_stop(&uart);
    return recovered ? ProbePass : ProbeFailRecovery;
}

int32_t labmate_busy_probe_app(void* args) {
    UNUSED(args);
    ProbeContext probe = {.state = ProbeReady};
    FuriMessageQueue* queue = furi_message_queue_alloc(8U, sizeof(InputEvent));
    ViewPort* viewport = view_port_alloc();
    view_port_draw_callback_set(viewport, probe_render, &probe);
    view_port_input_callback_set(viewport, probe_input, queue);
    Gui* gui = furi_record_open(RECORD_GUI);
    gui_add_view_port(gui, viewport, GuiLayerFullscreen);

    bool running = true;
    while(running) {
        InputEvent event;
        if(furi_message_queue_get(queue, &event, FuriWaitForever) != FuriStatusOk) continue;
        if(event.type != InputTypeShort) continue;
        if(event.key == InputKeyBack) {
            running = false;
        } else if(event.key == InputKeyOk) {
            probe.state = probe_execute();
            view_port_update(viewport);
        }
    }

    view_port_enabled_set(viewport, false);
    gui_remove_view_port(gui, viewport);
    furi_record_close(RECORD_GUI);
    view_port_free(viewport);
    furi_message_queue_free(queue);
    return 0;
}
