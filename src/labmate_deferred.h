#pragma once
#include <furi.h>
#include <gui/gui.h>
#include <stdint.h>
#include "labmate_internal.h"

/* Per-loop work snapshots, not shared global requests. */
typedef struct {
    bool logger_start_requested;
    bool logger_stop_requested;
    bool history_scan_requested;
    bool history_open_requested;
    bool history_close_requested;
    bool history_delete_requested;
    uint16_t history_delete_id;
    uint8_t history_delete_selected;
    bool profiles_read_requested;
    bool profiles_save_requested;
    bool profiles_delete_requested;
    LabMateProfileStore proposed_profiles;
    uint8_t proposed_copy;
    char pending_log_row[160];
    bool pending_log;
    bool uart_tx_requested;
    uint8_t uart_tx_len;
    uint8_t uart_tx_payload[LABMATE_UART_TX_CAP + 2U];
} LabMateDeferredWork;
void labmate_deferred_prepare(LabMateApp* app, LabMateDeferredWork* work);
void labmate_deferred_execute(LabMateApp* app, LabMateDeferredWork* work,
                              ViewPort* viewport);
