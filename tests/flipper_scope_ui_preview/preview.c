/* LabMate v1.9 simulated SINGLE-CHANNEL Logic Scope preview.
 * NO GPIO, IRQ, DWT, timer, serial, OTG, I2C, sensor or physical sampling.
 * The real, HAL-free trace and projection model generate mock waveforms.
 * ALWAYS display SIMULATED - NO GPIO on every 128x64 screen.
 * Built as its own FAP: NEVER overwrite production labmate.fap.
 */
#include <furi.h>
#include <gui/gui.h>
#include <gui/view_port.h>
#include <gui/canvas.h>
#include <input/input.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#include "../../src/labmate_scope_trace.c"
#include "../../src/labmate_scope_project.c"

#define SCOPE_UI_SCENES 9U
#define SCOPE_GRAPH_X 4
#define SCOPE_HIGH_Y 36
#define SCOPE_LOW_Y 51

typedef struct {
    LabMateScopeTrace trace;
    LabMateScopeProjection projection;
    uint8_t scene;
    bool model_ok;
    FuriMutex* lock;
} LabMateScopeDemo;

static const char* demo_title(uint8_t scene) {
    static const char* const titles[SCOPE_UI_SCENES] = {
        "CLEAN - TRACE", "DENSE - MULTIEDGE", "RISING - TRIGGER",
        "WAIT - NO EDGE", "STOP - NOT TRIG", "BUFFER - OVERFLOW",
        "CLOCK - FAULT", "LEFT - CROPPED", "ZERO - NO SPAN",
    };
    return titles[scene % SCOPE_UI_SCENES];
}

static const char* demo_no_wave_status(LabMateScopeViewState state) {
    switch(state) {
    case LabMateScopeViewWaitingTrigger: return "WAITING TRIGGER";
    case LabMateScopeViewNotTriggered: return "NOT TRIGGERED";
    case LabMateScopeViewNoSpan: return "NO TIME SPAN";
    case LabMateScopeViewOverflow: return "OVERFLOW";
    case LabMateScopeViewFault: return "CLOCK FAULT";
    default: return "NO WAVEFORM";
    }
}

static bool demo_expect(
    LabMateScopeDemo* demo, uint32_t token, uint32_t tick,
    uint8_t level, LabMateScopeFeedResult expected) {
    return labmate_scope_trace_feed(&demo->trace, token, tick, level) == expected;
}

static void demo_build(LabMateScopeDemo* demo) {
    labmate_scope_trace_init(&demo->trace);
    const uint8_t scene = demo->scene;
    uint32_t token = 0U;
    bool ok = true;
    uint32_t left = 0U;
    uint32_t right = 40U;

    if(scene == 1U) {
        ok = labmate_scope_trace_start(
            &demo->trace, LabMateScopeTriggerImmediate, 0U, 0U, &token);
        for(uint32_t i = 1U; i <= 5U && ok; ++i) {
            ok = demo_expect(demo, token, i, (uint8_t)(i & 1U),
                             LabMateScopeFeedRecorded);
        }
        if(ok) ok = demo_expect(demo, token, 1000U, 1U, LabMateScopeFeedIgnored);
        right = 1000U;
    } else if(scene == 2U) {
        ok = labmate_scope_trace_start(
            &demo->trace, LabMateScopeTriggerRising, 0U, 100U, &token);
        if(ok) ok = demo_expect(demo, token, 110U, 1U, LabMateScopeFeedTriggered);
        if(ok) ok = demo_expect(demo, token, 120U, 0U, LabMateScopeFeedRecorded);
        if(ok) ok = demo_expect(demo, token, 130U, 1U, LabMateScopeFeedRecorded);
        if(ok) ok = demo_expect(demo, token, 140U, 1U, LabMateScopeFeedIgnored);
        right = 30U;
    } else if(scene == 3U || scene == 4U) {
        ok = labmate_scope_trace_start(
            &demo->trace, LabMateScopeTriggerRising, 0U, 100U, &token);
        if(scene == 4U && ok) ok = labmate_scope_trace_stop(&demo->trace, token);
        right = 10U;
    } else if(scene == 5U) {
        ok = labmate_scope_trace_start(
            &demo->trace, LabMateScopeTriggerImmediate, 0U, 100U, &token);
        for(uint32_t i = 1U; i < LABMATE_SCOPE_MAX_EVENTS && ok; ++i) {
            ok = demo_expect(demo, token, 100U + i, (uint8_t)(i & 1U),
                             LabMateScopeFeedRecorded);
        }
        if(ok) ok = demo_expect(demo, token, 228U, 0U, LabMateScopeFeedOverflow);
        /* The omitted edge at offset 128 makes later signal UNKNOWN.
         * Project only through the last retained edge (127). */
        right = 127U;
    } else if(scene == 6U) {
        ok = labmate_scope_trace_start(
            &demo->trace, LabMateScopeTriggerImmediate, 0U, 100U, &token);
        if(ok) ok = demo_expect(demo, token, 110U, 1U, LabMateScopeFeedRecorded);
        if(ok) ok = demo_expect(demo, token, 110U, 0U, LabMateScopeFeedFault);
        right = 10U;
    } else if(scene == 8U) {
        ok = labmate_scope_trace_start(
            &demo->trace, LabMateScopeTriggerImmediate, 0U, 100U, &token);
        right = 10U;
    } else {
        ok = labmate_scope_trace_start(
            &demo->trace, LabMateScopeTriggerImmediate, 0U, 100U, &token);
        if(ok) ok = demo_expect(demo, token, 110U, 1U, LabMateScopeFeedRecorded);
        if(ok) ok = demo_expect(demo, token, 120U, 0U, LabMateScopeFeedRecorded);
        if(ok) ok = demo_expect(demo, token, 130U, 1U, LabMateScopeFeedRecorded);
        if(ok) ok = demo_expect(demo, token, 140U, 1U, LabMateScopeFeedIgnored);
        if(scene == 7U) left = 15U;
    }

    if(ok) ok = labmate_scope_project(&demo->trace, left, right, &demo->projection);
    demo->model_ok = ok;
}

static void demo_draw(Canvas* canvas, void* context) {
    const LabMateScopeDemo* demo = context;
    /* UI draw and input processing can run on separate framework threads.
     * Copy a single immutable snapshot under the short software mutex.
     * No hardware operations and no model mutation occur in Canvas code. */
    furi_mutex_acquire(demo->lock, FuriWaitForever);
    LabMateScopeProjection view = demo->projection;
    const uint8_t scene = demo->scene;
    const bool ok = demo->model_ok;
    furi_mutex_release(demo->lock);

    char index_text[12];
    canvas_clear(canvas);
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 2, 10, "SCOPE UX DEMO");
    canvas_set_font(canvas, FontSecondary);
    snprintf(index_text, sizeof(index_text), "%u/%u",
             (unsigned)(scene + 1U), (unsigned)SCOPE_UI_SCENES);
    canvas_draw_str(canvas, 104, 10, index_text);
    canvas_draw_line(canvas, 0, 12, 127, 12);
    canvas_draw_str(canvas, 2, 21, "SIMULATED - NO GPIO");
    canvas_draw_str(canvas, 2, 30, demo_title(scene));

    if(!ok) {
        canvas_draw_str(canvas, 15, 45, "MODEL ERROR");
    } else if(!view.has_waveform) {
        canvas_draw_str(canvas, 15, 45, demo_no_wave_status(view.state));
    } else {
        for(uint16_t col = 0U; col < LABMATE_SCOPE_GRAPH_COLUMNS; ++col) {
            const LabMateScopePixelColumn* p = &view.columns[col];
            const int16_t x = (int16_t)(SCOPE_GRAPH_X + col);
            const int16_t from_y = p->entering_level ? SCOPE_HIGH_Y : SCOPE_LOW_Y;
            const int16_t to_y = p->leaving_level ? SCOPE_HIGH_Y : SCOPE_LOW_Y;
            if(p->transitions >= 2U) {
                /* Intentionally emphasize UNRESOLVED multiple edges,
                 * never draw a fake clean pulse at subpixel density. */
                canvas_draw_box(canvas, x, SCOPE_HIGH_Y, 1, SCOPE_LOW_Y - SCOPE_HIGH_Y + 1);
            } else if(p->transitions == 1U) {
                canvas_draw_line(canvas, x, from_y, x, to_y);
            } else {
                canvas_draw_line(canvas, x, to_y, x, to_y);
            }
        }
        /* Semantically distinct text status on error/overflow as well
         * as black density bars, so no status relies on shape alone. */
        if(view.state == LabMateScopeViewOverflow)
            canvas_draw_str(canvas, 67, 44, "OVF");
        if(view.state == LabMateScopeViewFault)
            canvas_draw_str(canvas, 68, 44, "FAULT");
    }

    canvas_draw_line(canvas, 0, 56, 127, 56);
    canvas_draw_str(canvas, 2, 63, "L/R CASE  BACK EXIT");
}

static void demo_input(InputEvent* event, void* context) {
    /* Never block the GUI input callback while a full queue drains. */
    FuriMessageQueue* queue = context;
    furi_message_queue_put(queue, event, 0U);
}

int32_t labmate_scope_ui_preview_app(void* args) {
    UNUSED(args);
    LabMateScopeDemo demo = {0};
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
        if(furi_message_queue_get(queue, &event, FuriWaitForever) != FuriStatusOk)
            continue;
        if(event.type != InputTypeShort && event.type != InputTypeRepeat)
            continue;
        if(event.key == InputKeyBack) {
            running = false;
        } else if(event.key == InputKeyLeft || event.key == InputKeyRight) {
            furi_mutex_acquire(demo.lock, FuriWaitForever);
            if(event.key == InputKeyRight) {
                demo.scene = (uint8_t)((demo.scene + 1U) % SCOPE_UI_SCENES);
            } else {
                demo.scene = demo.scene ? (uint8_t)(demo.scene - 1U) :
                                          SCOPE_UI_SCENES - 1U;
            }
            demo_build(&demo);
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
