#include "labmate_ui_screens.h"
#include "labmate_comm_ui.h"
#include "labmate_uart.h"
#include <stdio.h>
#include <string.h>

/* GUI is passive. Never acquire UART, drain ISR bytes or send TX here. */
void draw_uart(Canvas* canvas, LabMateApp* app) {
    const LabMateUart* uart = &app->uart;
    /* UART TX is intentionally byte-for-byte the existing visual branch.
     * Its header, editor, and input behavior are outside COMM Step 2. */
    if(uart->tx_editing) {
        const char* state = uart->blocked ? "BUSY" :
                            uart->invalid_baud ? "BAUD" :
                            uart->dropped ? "DROP" :
                            uart->rx_errors ? "ERR" :
                            uart->active ? "RUN" : "STOP";
        labmate_comm_ui_header(canvas, "UART TX",
                               state, uart->active && !uart->blocked);
        canvas_set_font(canvas, FontSecondary);
        canvas_set_color(canvas, ColorBlack);
        (void)ui_kit_text(canvas, 4U, 21U, 120U,
                          "EDIT 12 CHARS  +CRLF", "EDIT +CRLF");
        (void)ui_kit_text(canvas, 4U, 37U, 120U, uart->tx_text, NULL);
        const uint8_t marker_x = (uint8_t)(4U + 6U * uart->tx_cursor);
        if(marker_x <= 122U)
            canvas_draw_line(canvas, marker_x, 40U, marker_x + 4U, 40U);
        (void)ui_kit_text(canvas, 4U, 50U, 120U,
                          uart->tx_sent ? "LAST TX SENT" : "^v CHAR  <> CURSOR",
                          uart->tx_sent ? "TX SENT" : "EDIT CHAR / CURSOR");
        labmate_comm_ui_keys(canvas, UiKitKeyOk, "Send",
                             UiKitKeyBack, "RX");
        return;
    }

    /* RX is display-only. The existing USART/ISR/queue/baud, text buffer,
     * input dispatch (including DOWN->TX), and navigation are untouched.
     * No synthetic session flag: a stopped, zero-byte RX is indistinguishable
     * from the never-started state with the current LabMateUart struct. */
    const bool completed = uart->rx_total != 0U || uart->dropped != 0U ||
                           uart->rx_errors != 0U;
    const UiKitInstrumentState instrument_state = uart->blocked ?
        UiKitInstrumentBusy : uart->invalid_baud ? UiKitInstrumentError :
        uart->active ? UiKitInstrumentLive :
        completed ? UiKitInstrumentStopped : UiKitInstrumentReady;

    /* First try the EXACT target FontPrimary x=9 title and right chip.
     * Native text widths decide if it fits; no overlap or clipped glyphs.
     * FontSecondary full-title is an explicit compact fallback, shifted
     * left at most 2px (x=7). Stopped has a long status: if even the
     * secondary title cannot fit, render 'UART' rather than corrupt pixels.
     * See COMM Step 2 documented visual deviations. */
    const bool pulse = (app->ui_frame & 16U) != 0U;
    if(!ui_kit_pixel_header(canvas, "UART receive", true, instrument_state, pulse)) {
        const uint8_t chip_w = ui_kit_state_chip_width(canvas, instrument_state);
        if(!chip_w) return;
        const uint16_t chip_x = (uint16_t)(127U - chip_w);
        canvas_set_font(canvas, FontSecondary);
        const uint16_t full_w = canvas_string_width(canvas, "UART receive");
        const bool normal_fit = 9U + full_w + 1U < chip_x;
        const bool shifted_fit = 7U + full_w + 1U < chip_x;
        const uint8_t title_x = normal_fit ? 9U : 7U;
        const char* title = (normal_fit || shifted_fit) ?
            "UART receive" : "UART";
        if(title == NULL) return; /* defensive only */
        canvas_set_font(canvas, (normal_fit || shifted_fit) ?
                        FontSecondary : FontPrimary);
        if((uint32_t)title_x + canvas_string_width(canvas, title) + 1U >= chip_x)
            return; /* fail-closed; never draw a collision */
        canvas_set_color(canvas, ColorBlack);
        canvas_draw_line(canvas, 5U, 2U, 2U, 5U);
        canvas_draw_line(canvas, 2U, 5U, 5U, 8U);
        canvas_draw_str(canvas, title_x, 9U, title);
        (void)ui_kit_state_chip(canvas, instrument_state, pulse);
    }

    /* Context: two complete English pin labels. A procedural dot replaces
     * the font-dependent UTF-8 middle dot without altering any pin number. */
    canvas_set_font(canvas, FontSecondary);
    const uint16_t left_w = canvas_string_width(canvas, "TX pin 13");
    const uint16_t right_w = canvas_string_width(canvas, "RX pin 14");
    const uint16_t dot_x = 4U + left_w + 4U;
    const uint16_t right_x = dot_x + 5U;
    canvas_set_color(canvas, ColorBlack);
    if(right_x + right_w <= 124U) {
        canvas_draw_str(canvas, 4U, 20U, "TX pin 13");
        canvas_draw_dot(canvas, dot_x, 17U);
        canvas_draw_str(canvas, right_x, 20U, "RX pin 14");
    } else {
        /* Explicit whole-string fallback, never a partially drawn word. */
        (void)ui_kit_text(canvas, 4U, 20U, 120U,
                          "TX pin 13  RX pin 14", "TX 13  RX 14");
    }

    /* Baud-rate pill: exact (58,24,66,12). A 2px leftward label shift is
     * permitted if the Flipper's measured font otherwise touches the pill. */
    const uint16_t baud_label_w = canvas_string_width(canvas, "Baud rate");
    if(4U + baud_label_w + 2U <= 58U)
        canvas_draw_str(canvas, 4U, 33U, "Baud rate");
    else if(2U + baud_label_w + 2U <= 58U)
        canvas_draw_str(canvas, 2U, 33U, "Baud rate");
    else
        (void)ui_kit_text(canvas, 4U, 33U, 50U, "Baud", NULL);

    canvas_draw_rframe(canvas, 58U, 24U, 66U, 12U, 3U);
    char baud[16];
    snprintf(baud, sizeof(baud), "%lu",
             (unsigned long)labmate_uart_baud(uart));
    canvas_set_font(canvas, FontPrimary);
    const uint16_t baud_w = canvas_string_width(canvas, baud);
    if(baud_w && baud_w <= 58U)
        canvas_draw_str(canvas, 91U - baud_w / 2U, 33U, baud);

    /* The three unmodified counters have genuine, distinct meanings:
     * rx_total = bytes consumed from the RX queue; dropped = UART ISR
     * bytes rejected by its bounded stream; rx_errors = UART error events.
     * Large numbers are DISPLAY ONLY rounded down to one decimal and
     * suffixed k/M/G; full uint32_t counters are never modified/capped. */
    const uint32_t counts[3] = {
        uart->rx_total, uart->dropped, uart->rx_errors};
    static const uint8_t col_x[3] = {4U,46U,88U};
    static const char* const labels[3] = {
        "Received","Dropped","Errors"};
    static const char* const compact_labels[3] = {
        "Recv","Drop","Errors"};
    for(uint8_t i = 0U; i < 3U; ++i) {
        const uint16_t available = i < 2U ?
            (uint16_t)(col_x[i+1U] - col_x[i] - 2U) :
            (uint16_t)(127U - col_x[i]);
        canvas_set_font(canvas, FontSecondary);
        const char* label = canvas_string_width(canvas, labels[i]) <= available ?
            labels[i] : compact_labels[i];
        if(canvas_string_width(canvas, label) <= available)
            canvas_draw_str(canvas, col_x[i], 43U, label);

        const uint32_t n = counts[i];
        char value[20];
        if(n < 10000U)
            snprintf(value, sizeof(value), "%lu", (unsigned long)n);
        else if(n < 100000U)
            snprintf(value, sizeof(value), "%lu.%luk",
                     (unsigned long)(n/1000U),
                     (unsigned long)((n%1000U)/100U));
        else if(n < 1000000U)
            snprintf(value, sizeof(value), "%luk", (unsigned long)(n/1000U));
        else if(n < 100000000U)
            snprintf(value, sizeof(value), "%lu.%luM",
                     (unsigned long)(n/1000000U),
                     (unsigned long)((n%1000000U)/100000U));
        else if(n < 1000000000U)
            snprintf(value, sizeof(value), "%luM",
                     (unsigned long)(n/1000000U));
        else
            snprintf(value, sizeof(value), "%lu.%luG",
                     (unsigned long)(n/1000000000U),
                     (unsigned long)((n%1000000000U)/100000000U));

        canvas_set_font(canvas, FontPrimary);
        /* If a changed device font exceeds the 42px column, use an honest
         * shorter rendering, not truncation, overflow or false zero. */
        if(canvas_string_width(canvas, value) <= available)
            canvas_draw_str(canvas, col_x[i], 52U, value);
        else {
            canvas_set_font(canvas, FontSecondary);
            if(canvas_string_width(canvas, value) <= available)
                canvas_draw_str(canvas, col_x[i], 52U, value);
        }
    }

    (void)ui_kit_key_hint(canvas, 4U, UiKitKeyOk,
                          uart->active ? "Stop" : "Start");
    /* Kept visible while Live per target specification: the existing input
     * handler correctly ignores LR baud changes during an active session.
     * DOWN still opens the unchanged TX editor; it has no footer chip. */
    (void)ui_kit_key_hint(canvas, 70U, UiKitKeyLeftRight, "Baud");
    canvas_set_color(canvas, ColorBlack);
}
