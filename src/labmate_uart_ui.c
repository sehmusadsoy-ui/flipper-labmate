#include "labmate_ui_screens.h"
#include "labmate_comm_ui.h"
#include "labmate_uart.h"
#include <stdio.h>
#include <string.h>

/* GUI is passive. Never acquire UART, drain ISR bytes or send TX here. */
void draw_uart(Canvas* canvas, LabMateApp* app) {
    const LabMateUart* uart = &app->uart;
    const char* state = uart->blocked ? "BUSY" :
                        uart->invalid_baud ? "BAUD" :
                        uart->dropped ? "DROP" :
                        uart->rx_errors ? "ERR" :
                        uart->active ? "RUN" : "STOP";
    labmate_comm_ui_header(canvas, uart->tx_editing ? "UART TX" : "UART RX",
                           state, uart->active && !uart->blocked);
    canvas_set_font(canvas, FontSecondary);
    canvas_set_color(canvas, ColorBlack);
    if(uart->tx_editing) {
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

    char status[32];
    snprintf(status, sizeof(status), "TX13 RX14 %lu",
             (unsigned long)labmate_uart_baud(uart));
    (void)ui_kit_text(canvas, 4U, 20U, 120U, status, "TX13 RX14");

    char received[20], dropped[24];
    snprintf(received, sizeof(received), "R:%lu",
             (unsigned long)(uart->rx_total > 999999U ? 999999U : uart->rx_total));
    snprintf(dropped, sizeof(dropped), "D:%lu E:%lu",
             (unsigned long)(uart->dropped > 999U ? 999U : uart->dropped),
             (unsigned long)(uart->rx_errors > 999U ? 999U : uart->rx_errors));
    (void)ui_kit_stat_row(canvas, 22U, received, dropped);

    if(uart->rx_total == 0U) {
        (void)ui_kit_text(canvas, 4U, 43U, 120U,
                          uart->active ? "WAITING RX..." : "OK START / LR BAUD",
                          uart->active ? "WAIT RX" : "OK START");
    } else {
        const uint8_t first = uart->terminal.cursor_row < 2U ? 0U : 1U;
        for(uint8_t i = 0U; i < 2U; ++i) {
            (void)ui_kit_text(canvas, 4U, (uint8_t)(41U + 9U * i), 120U,
                              uart->terminal.rows[first + i], NULL);
        }
    }
    if(uart->active)
        labmate_comm_ui_keys(canvas, UiKitKeyOk, "Stop",
                             UiKitKeyDown, "TX");
    else
        labmate_comm_ui_keys(canvas, UiKitKeyOk, "Start",
                             UiKitKeyLeftRight, "Baud");
}
