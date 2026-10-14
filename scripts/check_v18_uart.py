#!/usr/bin/env python3
"""Static guards against unsafe UART ownership and ISR/UI coupling."""
from pathlib import Path
src = Path(__file__).resolve().parents[1] / "src"
read = lambda n: (src / n).read_text()
uart = read("labmate_uart.c")
ui = read("labmate_uart_ui.c")
keys = read("labmate_input_uart.c")
app = read("labmate.c")
dispatch = read("labmate_input.c")
menu = read("labmate_input_menu.c")
deferred = read("labmate_deferred.c")
nav = read("labmate_navigation.c")
assert "FuriHalSerialIdUsart" in uart
for fn in ("expansion_is_connected(", "expansion_disable(", "expansion_enable(",
           "furi_hal_serial_control_acquire(", "furi_hal_serial_control_release(",
           "furi_hal_serial_async_rx_start(", "furi_hal_serial_async_rx_stop(",
           "furi_hal_serial_deinit(", "furi_hal_serial_tx_wait_complete(",
           "furi_hal_serial_is_baud_rate_supported("):
    assert fn in uart, fn
assert "furi_stream_buffer_send(uart->stream, &data, 1U, 0U)" in uart
assert "uart->dropped++;" in uart
# ESP32 115200 stress originally lost 52 bytes in a 256-byte queue.
# Mitigation retains visible overflow accounting; it is NOT a physical PASS.
assert "#define LABMATE_UART_RX_QUEUE 1024U" in read("labmate_uart.h")
assert "for(uint8_t round = 0; round < 16U; ++round)" in uart
callback = uart.split("static void uart_rx_callback(", 1)[1].split("bool labmate_uart_start(", 1)[0]
for forbidden in ("canvas_", "storage_", "furi_mutex_", "furi_hal_serial_tx("):
    assert forbidden not in callback, forbidden
assert "furi_stream_buffer_receive(" in uart and "labmate_uart_text_push(" in uart
assert "work->uart_tx_requested = true;" in keys
assert "labmate_uart_send(" in deferred
assert "labmate_uart_stop(&app->uart);" in app
assert "labmate_uart_poll(&app->uart);" in app
# New app starts at default 115200; returning to UART preserves user-selected baud.
assert "labmate_uart_reset(&app->uart);" in app
assert "labmate_uart_reenter(&app->uart);" in menu
assert "labmate_uart_reset(&app->uart);" not in menu
assert "void labmate_uart_reenter(LabMateUart* uart)" in uart
reenter = uart.split("void labmate_uart_reenter(LabMateUart* uart) {", 1)[1].split(
    "\n}", 1
)[0]
assert "saved_baud_index = uart->baud_index;" in reenter
assert "labmate_uart_stop(uart);" in reenter
assert "labmate_uart_reset(uart);" in reenter
assert "uart->baud_index =" in reenter
assert reenter.index("saved_baud_index =") < reenter.index("labmate_uart_reset(uart);") < reenter.index("uart->baud_index =")
assert "LabMateScreenUart:" in dispatch
assert "LabMateToolUart" in nav
assert "LabMateGroupComm" in read("labmate_navigation.h")
assert "draw_uart(canvas, app);" in read("labmate_view.c")
for forbidden in ("furi_hal_serial_", "expansion_", "storage_"):
    assert forbidden not in ui
assert "labmate_uart_edit_change(" in keys
assert "labmate_uart_next_baud(" in keys
assert "labmate_uart_stop(uart);" in keys
print("LabMate UART ownership, RX ISR separation, explicit TX and cleanup PASS")
