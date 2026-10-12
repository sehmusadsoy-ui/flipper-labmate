#include "labmate_ui_screens.h"
#include "labmate_ui_primitives.h"
#include "labmate_uart.h"
#include <stdio.h>
#include <string.h>

/* GUI is passive. Never acquire UART, drain ISR bytes or send TX here. */
void draw_uart(Canvas* canvas, LabMateApp* app) {
    const LabMateUart* uart = &app->uart;
    ui_draw_header(canvas, uart->tx_editing ? "UART TX" : "UART RX");
    ui_badge(canvas, 87, 1, 39,
             uart->blocked ? "BUSY" :
             uart->invalid_baud ? "BAUD" :
             uart->dropped ? "DROP" :
             uart->rx_errors ? "ERR" : uart->active ? "RUN" : "STOP", false);
    canvas_set_font(canvas, FontSecondary);
    if(uart->tx_editing) {
        canvas_draw_str(canvas, 3, 22, "EDIT 12 CHARS  +CRLF");
        canvas_draw_str(canvas, 4, 37, uart->tx_text);
        const uint8_t marker_x = (uint8_t)(4U + 6U * uart->tx_cursor);
        canvas_draw_line(canvas, marker_x, 40, marker_x + 4U, 40);
        canvas_draw_str(canvas, 3, 50,
                        uart->tx_sent ? "LAST TX SENT" : "^v CHAR  <> CURSOR");
        ui_footer_pair(canvas, "OK", "SEND", "BK", "RX");
        return;
    }
    char status[24];
    snprintf(status, sizeof(status), "TX13 RX14 %lu", (unsigned long)labmate_uart_baud(uart));
    canvas_draw_str(canvas, 2, 23, status);
    /* Bounded 128px UI: prevent large counters from drawing off screen. */
    snprintf(status, sizeof(status), "R:%lu D:%lu E:%lu",
             (unsigned long)(uart->rx_total > 999999U ? 999999U : uart->rx_total),
             (unsigned long)(uart->dropped > 999U ? 999U : uart->dropped),
             (unsigned long)(uart->rx_errors > 999U ? 999U : uart->rx_errors));
    canvas_draw_str(canvas, 2, 32, status);
    if(uart->rx_total == 0U) {
        canvas_draw_str(canvas, 4, 43, uart->active ? "WAITING RX..." : "OK START / LR BAUD");
    } else {
        const uint8_t first = uart->terminal.cursor_row < 2U ? 0U : 1U;
        for(uint8_t i = 0U; i < 2U; ++i) {
            canvas_draw_str(canvas, 3, (uint8_t)(43U + 9U * i),
                            uart->terminal.rows[first + i]);
        }
    }
    if(uart->active) ui_footer_pair(canvas, "OK", "STOP", "DN", "TX");
    else ui_footer_pair(canvas, "OK", "START", "LR", "BAUD");
}
